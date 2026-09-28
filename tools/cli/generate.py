#!/usr/bin/env python3
"""Generate a worker prompt from a .md file and invoke the worker."""

import base64
import concurrent.futures
import difflib
import importlib
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse the YAML frontmatter block and return (settings, prompt)."""
    parts = content.split("---", 2)
    if len(parts) != 3:
        raise ValueError("missing frontmatter delimiters (---)")

    settings: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        settings[key.strip()] = value.strip()

    prompt = parts[2].strip()
    return settings, prompt


MEDIA_SCALAR_KEYS = {"first_frame", "last_frame"}
MEDIA_LIST_KEYS = {"ref_images", "ref_videos", "ref_video_audios", "ref_audios"}


def _strip_data_url(value: str) -> str:
    """Strip a data:...;base64, prefix, returning raw base64."""
    if value.startswith("data:") and "," in value:
        return value.split(",", 1)[1]
    return value


MEDIA_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
               ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".aac")


def _looks_like_path(value: str) -> bool:
    """Heuristic: slashes, leading ~/., or a known media extension."""
    return (
        "/" in value
        or "\\" in value
        or value.startswith(("~", "."))
        or value.lower().endswith(MEDIA_EXTS)
    )


def _looks_like_base64(value: str) -> bool:
    """Strict-decodable and long enough to be a real payload, not a path."""
    s = _strip_data_url(value).strip()
    if len(s) < 64:
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False


def _suggest_similar(filename: str, md_dir: Path, limit: int = 3) -> list[str]:
    """Find same-named files under md_dir and its parent, else close names."""
    hits: list[str] = []
    for root in (md_dir, md_dir.parent):
        if not root.is_dir():
            continue
        try:
            for p in root.rglob(filename):
                if p.is_file():
                    try:
                        import os as _os

                        hits.append(_os.path.relpath(p, md_dir))
                    except ValueError:
                        hits.append(str(p))
                    if len(hits) >= limit:
                        return hits
        except OSError:
            continue
    if not hits and filename:
        pool: list[str] = []
        for root in (md_dir, md_dir.parent):
            if not root.is_dir():
                continue
            try:
                pool.extend(p.name for p in root.iterdir())
            except OSError:
                continue
        hits.extend(difflib.get_close_matches(filename, pool, n=limit, cutoff=0.6))
    return hits


def _path_to_b64(value: str, md_dir: Path, field: str = "media") -> str:
    """Resolve a media value to raw base64.

    Real base64 payloads pass through (data-URL prefix stripped). Existing
    files are read and encoded. Anything path-like that does not resolve
    raises FileNotFoundError immediately — a missing file must never reach
    a worker as a string.
    """
    if _looks_like_base64(value):
        return _strip_data_url(value).strip()
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = md_dir / candidate
    if candidate.is_file():
        try:
            return base64.b64encode(candidate.read_bytes()).decode("ascii")
        except OSError as exc:
            raise FileNotFoundError(
                f"{field}: cannot read file '{value}': {exc}"
            ) from exc
    if _looks_like_path(value):
        suggestions = _suggest_similar(Path(value).name, md_dir)
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise FileNotFoundError(
            f"{field}: file not found: '{value}' (resolved against {md_dir}/).{hint}"
        )
    return _strip_data_url(value)


def resolve_media_value(value: Any, md_dir: Path, field: str = "media") -> Any:
    """Convert file paths to base64 for image/audio inputs. Pass through None."""
    if value is None:
        return None
    if isinstance(value, list):
        return [
            _path_to_b64(v, md_dir, f"{field}[{i}]") if isinstance(v, str) else v
            for i, v in enumerate(value)
        ]
    if isinstance(value, str):
        return _path_to_b64(value, md_dir, field)
    return value


def _repo_root() -> Path:
    """Repo root anchored at this file, independent of cwd.

    This file lives at tools/cli/generate.py, three levels below the root.
    """
    return Path(__file__).resolve().parent.parent.parent


def find_contract(contract_name: str) -> Path | None:
    """Find the contract JSON whose title matches contract_name.

    Canonical source is packages/contracts; workers/ is a fallback for
    contracts not yet promoted (e.g. tiny_sd).
    """
    roots = [_repo_root() / "packages" / "contracts", _repo_root() / "workers"]
    for root in roots:
        if not root.is_dir():
            continue
        for json_path in sorted(root.rglob("contracts/*.json")) + sorted(
            (root / "src").rglob("*.json") if (root / "src").is_dir() else []
        ):
            try:
                data = json.loads(json_path.read_text())
            except (OSError, ValueError):
                continue
            title = data.get("input", {}).get("title") or data.get("title")
            if title == contract_name:
                return json_path
    return None


def resolve_family_dir(contract_path: Path, slug: str) -> Path | None:
    """Return the workers/<family> dir owning this contract.

    Contracts under workers/ already sit beside their workers. Centralized
    contracts under packages/contracts/ resolve via the same-named copy in
    the workers tree (every promoted slug keeps one).
    """
    candidate = contract_path.parent.parent
    if list(candidate.glob("worker_*.py")):
        return candidate
    for json_path in sorted((_repo_root() / "workers").rglob(f"contracts/{slug}.json")):
        return json_path.parent.parent
    return None


def find_workers(model_dir: Path) -> list[Path]:
    """List all worker_*.py files in the model folder."""
    return sorted(model_dir.glob("worker_*.py"))


def select_worker_fzf(workers: list[Path]) -> Path | None:
    """Use fzf to let the user select a worker."""
    if not workers:
        return None
    worker_names = [w.name for w in workers]
    fzf_input = "\n".join(worker_names)
    try:
        proc = subprocess.run(
            ["fzf", "--prompt", "Select worker: "],
            input=fzf_input,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Error: fzf not found. Please install fzf.", file=sys.stderr)
        return None
    selected_name = proc.stdout.strip()
    if not selected_name:
        return None
    for w in workers:
        if w.name == selected_name:
            return w
    return None


def get_provider_from_worker(worker_path: Path) -> str:
    """Return provider string from worker filename."""
    name = worker_path.name
    if name.startswith("worker_beam_asgi_"):
        return "asgi"
    if name.startswith(("worker_beam_tq_", "worker_beam_asgi_")):
        return "beam"
    if name.startswith("worker_flash_cls_"):
        return "flash"
    if name.startswith("worker_modal_cls_"):
        return "modal"
    raise ValueError(f"Unknown worker pattern: {name}")


def load_worker_module(worker_path: Path):
    """Load a worker module from a file path."""
    # Add the parent directory of the workers package to sys.path
    # so that imports like "workers.flux2.*" work
    workers_dir = worker_path.parent.parent  # workers/flux2 -> workers
    repo_root = workers_dir.parent          # workers -> repo root
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        # Compute the module name relative to the repo root
        # Example: workers/flux2/worker_beam_tq_flux2_klein9b.py -> workers.flux2.worker_beam_tq_flux2_klein9b
        rel_path = worker_path.relative_to(repo_root)
        module_name = str(rel_path.with_suffix('')).replace('/', '.')
        module = importlib.import_module(module_name)
        return module
    finally:
        # Remove the added path if we added it
        if str(repo_root) in sys.path:
            sys.path.remove(str(repo_root))


def invoke_beam(worker_module, good: dict[str, Any]):
    """Invoke a Beam worker via task queue."""
    if not hasattr(worker_module, "dispatch"):
        raise AttributeError("Worker module has no 'dispatch' attribute")
    dispatch = worker_module.dispatch
    print("Dispatching task to Beam...")
    task = dispatch.put(**good)
    print(f"Task ID: {task.id}")
    print("Waiting for result...")
    out = task.result(wait=True)
    return out


def invoke_flash(worker_module, good: dict[str, Any]):
    """Invoke a Flash worker in-process."""
    # Find the worker class: look for a class that has a generate method and is defined in this module
    candidate_classes = []
    for name in dir(worker_module):
        obj = getattr(worker_module, name)
        if isinstance(obj, type) and hasattr(obj, "generate"):
            candidate_classes.append(obj)
    if not candidate_classes:
        raise ValueError("No worker class with generate method found in flash worker module")
    # If there are multiple, pick the first one (should be only one)
    WorkerClass = candidate_classes[0]
    print(f"Instantiating flash worker: {WorkerClass.__name__}")
    worker = WorkerClass()
    print("Running generate...")
    # We need to capture stdout/stderr from the worker's generate method.
    # Since it's in-process, we can redirect? But we want to see the output as it happens.
    # We'll just call it and let it print to our stdout/stderr.
    out = worker.generate(**good)
    return out


def invoke_modal(worker_module, good: dict[str, Any]):
    """Invoke a Modal worker."""
    # Parse the worker file to get app name and class name
    worker_file = worker_module.__file__
    if worker_file is None:
        raise ValueError("Could not determine worker file path")
    with open(worker_file) as f:
        lines = f.readlines()
    app_name = None
    class_name = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("app = modal.App("):
            # Extract the string inside the parentheses
            # Simple parsing: find the first and second quote
            if '"' in stripped:
                parts = stripped.split('"')
                if len(parts) >= 2:
                    app_name = parts[1]
            elif "'" in stripped:
                parts = stripped.split("'")
                if len(parts) >= 2:
                    app_name = parts[1]
        if stripped.startswith("@app.cls"):
            # The next non-empty line that starts with "class " is the class
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("class "):
                    # Extract class name
                    class_line = lines[j].strip()
                    # class ClassName(...):
                    if "class " in class_line:
                        class_part = class_line.split("class ", 1)[1]
                        class_name = class_part.split("(", 1)[0].split(":", 1)[0].strip()
                    break
    if app_name is None:
        raise ValueError("Could not find app name in modal worker file")
    if class_name is None:
        raise ValueError("Could not find class name in modal worker file")
    print(f"Modal app: {app_name}, class: {class_name}")
    import modal
    print("Looking up modal class...")
    Cls = modal.Cls.from_name(app_name, class_name)
    print("Spawning generate...")
    # Record start time for logs
    start_time = datetime.now(UTC) - timedelta(seconds=5)  # a bit before to catch any logs
    call = Cls().generate.spawn(**good)
    fc_id = getattr(call, "object_id", "") or ""
    print(f"Call ID: {fc_id}")
    print("Waiting for result (polling container logs every 10s)...")
    # Clean UTC ISO for --since: strftime, never isoformat()+"Z" (double tz).
    since_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    poll_cmd = ["modal", "app", "logs", app_name, "--since", since_str,
                "--timestamps", "--tail", "200"]
    if fc_id:
        poll_cmd += ["--function-call", fc_id]
    seen: Counter[str] = Counter()
    cli_missing = False

    def _poll_logs() -> None:
        """Fetch scoped logs, print only lines not seen before. No repeats."""
        nonlocal seen, cli_missing
        if cli_missing:
            return
        try:
            proc = subprocess.run(
                poll_cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except FileNotFoundError:
            cli_missing = True
            print("modal CLI not found, waiting without live logs", file=sys.stderr)
            return
        except subprocess.TimeoutExpired:
            print("(log poll timed out, retrying)", file=sys.stderr)
            return
        if proc.returncode != 0:
            err = (proc.stderr or "").strip()
            if err:
                print(f"(log poll failed: {err})", file=sys.stderr)
            return
        counts: Counter[str] = Counter()
        for line in proc.stdout.splitlines():
            counts[line] += 1
            if counts[line] > seen[line]:
                print(line)
        seen = counts

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(call.get, timeout=3600)
        try:
            while True:
                try:
                    out = future.result(timeout=10)
                    break
                except concurrent.futures.TimeoutError:
                    _poll_logs()
        except Exception as exc:
            print(f"\n[ERR] Worker invocation failed: {exc}", file=sys.stderr)
            _poll_logs()  # final lines before the traceback lands
            raise
        _poll_logs()  # final catch-up on success
    return out


def invoke_asgi(worker_module, good: dict[str, Any]):
    """Refuse interactive invocation of an ASGI worker.

    ASGI workers serve HTTP via Beam; generate cannot dispatch to them.
    Start the endpoint and POST the payload instead.
    """
    name = getattr(worker_module, "__name__", str(worker_module))
    raise ValueError(
        f"{name} is a Beam ASGI worker: start its HTTP endpoint "
        "and POST the payload instead of using generate"
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: generate <path/to/prompt.md>", file=sys.stderr)
        return 1

    md_path = Path(sys.argv[1])
    try:
        content = md_path.read_text()
        settings, prompt = parse_frontmatter(content)
    except (OSError, ValueError) as exc:
        print(f"Error reading prompt file: {exc}", file=sys.stderr)
        return 1

    contract_name = settings.get("contract")
    if not contract_name:
        print("Error: missing 'contract:' in frontmatter", file=sys.stderr)
        return 1

    # Remove contract from settings to get the input dict
    good = {k: v for k, v in settings.items() if k != "contract"}
    # Add the prompt to the input dict
    good["prompt"] = prompt
    # Convert string values to appropriate types? We'll keep as strings and let the model handle it.
    # But note: the frontmatter values are strings, but the contract may expect integers, etc.
    # We'll do a simple conversion: if the string is a number, convert to int or float.
    # This is a best-effort; the model validation will catch errors.
    def convert_value(v):
        if v.lower() == "null":
            return None
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        # Try int
        try:
            return int(v)
        except ValueError:
            pass
        # Try float
        try:
            return float(v)
        except ValueError:
            pass
        # Try JSON array (e.g., "[]" or '["item1", "item2"]')
        if v.startswith('[') and v.endswith(']'):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                pass  # Fall through to string if not valid JSON
        # Return as string
        return v

    # Convert types, but NEVER coerce the prompt: a prompt reading
    # "null"/"true"/"0"/"[x]" must stay exactly that string.
    good = {k: (v if k == "prompt" else convert_value(v)) for k, v in good.items()}
    # Resolve media file paths (relative to the md file) to base64.
    # Missing files are fatal here — never ship a path string to a worker.
    md_dir = md_path.parent
    try:
        for key in MEDIA_SCALAR_KEYS | MEDIA_LIST_KEYS:
            if key in good:
                good[key] = resolve_media_value(good[key], md_dir, field=key)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    contract_path = find_contract(contract_name)
    if contract_path is None:
        print(f"Error: no contract found for '{contract_name}'", file=sys.stderr)
        return 1

    # Narrow to workers for this contract (contract stem e.g.
    # minimax_h3_turbo_fl2va matches worker_*_minimax_h3_turbo_fl2va.py).
    slug = contract_path.stem
    family_dir = resolve_family_dir(contract_path, slug)
    if family_dir is None:
        print(f"Error: no worker family found for contract '{slug}'", file=sys.stderr)
        return 1
    workers = find_workers(family_dir)
    if not workers:
        print(f"Error: no workers found in {family_dir}", file=sys.stderr)
        return 1
    slugged = [w for w in workers if slug in w.stem]
    if slugged:
        workers = slugged
    else:
        print(f"Warning: no worker filename matches contract '{slug}', offering all", file=sys.stderr)

    # Use fzf for interactive selection if stdin is a TTY, otherwise pick worker.
    # WORKER_PROVIDER env can force a provider (beam|flash|modal).
    import os as _os

    forced = (_os.environ.get("WORKER_PROVIDER") or "").strip().lower() or None
    if forced:
        matches = [w for w in workers if get_provider_from_worker(w) == forced]
        if not matches:
            print(f"Error: no '{forced}' worker in {family_dir}", file=sys.stderr)
            return 1
        worker_path = matches[0]
        print(f"[Forced provider={forced}] Selected worker: {worker_path.name}")
    elif sys.stdin.isatty():
        worker_path = select_worker_fzf(workers)
        if worker_path is None:
            print("Error: no worker selected", file=sys.stderr)
            return 1
    else:
        # Non-interactive: prefer modal (beam logs stream is unreliable), else first.
        modal_workers = [w for w in workers if get_provider_from_worker(w) == "modal"]
        worker_path = modal_workers[0] if modal_workers else workers[0]
        print(f"[Non-interactive mode] Auto-selected worker: {worker_path.name}")

    provider = get_provider_from_worker(worker_path)
    print(f"Selected provider: {provider}")
    print(f"Selected worker: {worker_path.name}")

    try:
        worker_module = load_worker_module(worker_path)
    except Exception as exc:
        print(f"Error loading worker module: {exc}", file=sys.stderr)
        return 1

    try:
        if provider == "beam":
            out = invoke_beam(worker_module, good)
        elif provider == "flash":
            out = invoke_flash(worker_module, good)
        elif provider == "modal":
            out = invoke_modal(worker_module, good)
        elif provider == "asgi":
            out = invoke_asgi(worker_module, good)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    except Exception as exc:
        print(f"\n[\033[31mERR\033[0m] Worker invocation failed: {exc}", file=sys.stderr)
        # Print the exception details
        import traceback
        traceback.print_exc()
        return 1

    # Now handle the output
    # We need to check the contract's output schema to see if it has an artifact.presigned_url
    # Load the contract JSON again
    contract_data = json.loads(contract_path.read_text())
    output_schema = contract_data.get("output", {})
    output_properties = output_schema.get("properties", {})
    # Check if there is an artifact.presigned_url path
    has_artifact_url = False
    if "artifact" in output_properties:
        artifact_props = output_properties["artifact"].get("properties", {})
        if "presigned_url" in artifact_props:
            has_artifact_url = True

    if has_artifact_url:
        # Contract expects artifact.presigned_url
        if isinstance(out, dict) and "artifact" in out and isinstance(out["artifact"], dict) and "presigned_url" in out["artifact"]:
            presigned_url = out["artifact"]["presigned_url"]
            print(f"\n[\033[32mOK\033[0m] Success! Artifact URL: {presigned_url}")
        else:
            # Output doesn't match contract — treat as failure
            print(f"\n[\033[31mERR\033[0m] Worker returned invalid output: {json.dumps(out)}")
            return 1
    else:
        # No artifact in contract — pretty-print entire output
        print("\n[\033[32mOK\033[0m] Success! Output:")
        print(json.dumps(out, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
