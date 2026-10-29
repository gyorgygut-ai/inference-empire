"""Seed missing Hugging Face snapshots into their declared Beam volumes."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
WORKERS_ROOT = ROOT / "apps" / "workers"


@dataclass(frozen=True)
class Model:
    name: str
    repo_id: str
    cache_path: str
    volume: str
    declaration: Path


def declared_models(root: Path = ROOT) -> list[Model]:
    """Read literal worker MODEL_CACHES declarations without importing workers."""
    models: list[Model] = []
    workers_root = root / "apps" / "workers"

    for declaration in sorted(workers_root.glob("*/shared/worker_*.py")):
        tree = ast.parse(declaration.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "MODEL_CACHES"
                for target in node.targets
            ):
                continue

            entries = ast.literal_eval(node.value)
            if not isinstance(entries, dict):
                raise ValueError(f"{declaration}: MODEL_CACHES must be a dictionary")

            for name, values in entries.items():
                if not isinstance(name, str) or not isinstance(values, dict):
                    raise ValueError(f"{declaration}: invalid MODEL_CACHES entry")
                url = values.get("url")
                cache_path = values.get("path")
                if not isinstance(url, str) or not isinstance(cache_path, str):
                    raise ValueError(f"{declaration}: {name} needs string url and path")
                parsed = urlparse(url)
                if parsed.scheme != "https" or parsed.netloc != "huggingface.co":
                    raise ValueError(f"{declaration}: unsupported Hugging Face URL {url!r}")
                repo_id = parsed.path.strip("/")
                if not repo_id:
                    raise ValueError(f"{declaration}: empty Hugging Face repo in {url!r}")

                models.append(
                    Model(
                        name=name,
                        repo_id=repo_id,
                        cache_path=cache_path,
                        volume=f"model-cache-{name}",
                        declaration=declaration,
                    )
                )

    return models


def run_beam(*args: str) -> str:
    result = subprocess.run(
        ["uvx", "--from", "beam-client==0.2.233", "beam", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"beam {' '.join(args)} failed: {detail}")
    return result.stdout


def _json_payload(output: str) -> Any:
    """Decode the JSON payload, tolerating CLI status text around it."""
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    decoder = json.JSONDecoder()
    starts = sorted(
        index for index, character in enumerate(output) if character in "[{"
    )
    for start in starts:
        try:
            return decoder.raw_decode(output[start:])[0]
        except json.JSONDecodeError:
            continue
    raise ValueError(f"Beam did not return JSON: {output.strip()}")


def existing_volumes() -> set[str]:
    payload = _json_payload(run_beam("volume", "list", "--format", "json"))
    if not isinstance(payload, list):
        raise ValueError("Beam volume list JSON must be a list")
    return {
        entry["name"]
        for entry in payload
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }


def _entry_name(entry: dict[str, Any]) -> str | None:
    for key in ("path", "name", "key"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value.removeprefix("./").strip("/")
    return None


def _walk_volume(volume: str, path: str, prefix: str = "") -> set[str]:
    """Recursively list a Beam path and return file paths relative to it."""
    payload = _json_payload(run_beam("ls", f"{volume}/{path}", "--format", "json"))
    if not isinstance(payload, list):
        raise ValueError(f"Beam listing for {volume}/{path} must be a JSON list")

    files: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = _entry_name(entry)
        if name is None:
            continue
        is_dir = entry.get("is_dir", entry.get("is_directory", entry.get("IsDir", False)))
        relative_path = f"{prefix}/{name}".strip("/")
        child_path = f"{path.rstrip('/')}/{name}"
        if is_dir:
            files.update(_walk_volume(volume, child_path, relative_path))
        else:
            files.add(relative_path)
    return files


def snapshot_is_complete(volume: str, snapshot_path: str, expected_files: list[str]) -> bool:
    """A snapshot is seeded only if every file in the HF revision is present."""
    if not expected_files:
        return False
    listed = _walk_volume(volume, snapshot_path)
    return all(expected in listed for expected in expected_files)


def _cache_repo_dir(cache_root: Path, repo_id: str) -> Path:
    return cache_root / f"models--{repo_id.replace('/', '--')}"


def seed_model(model: Model, volume_names: set[str]) -> None:
    from huggingface_hub import HfApi, snapshot_download

    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    revision = api.model_info(model.repo_id).sha
    if not revision:
        raise RuntimeError(f"Hugging Face did not return a revision for {model.repo_id}")
    expected_files = api.list_repo_files(model.repo_id, revision=revision)
    repo_cache_name = f"models--{model.repo_id.replace('/', '--')}"
    snapshot_path = f"{repo_cache_name}/snapshots/{revision}"

    if model.volume in volume_names and snapshot_is_complete(
        model.volume, snapshot_path, expected_files
    ):
        print(f"{model.name}: Beam volume already contains the complete snapshot.")
        return

    if model.volume not in volume_names:
        print(f"{model.name}: creating Beam volume {model.volume}.")
        run_beam("volume", "create", model.volume)
        volume_names.add(model.volume)

    print(f"{model.name}: downloading {model.repo_id}@{revision}.", flush=True)
    with tempfile.TemporaryDirectory(prefix="beam-model-seed-") as temporary:
        cache_root = Path(temporary) / "cache"
        snapshot_download(
            repo_id=model.repo_id,
            revision=revision,
            cache_dir=cache_root,
            token=token,
        )
        staged_repo = _cache_repo_dir(cache_root, model.repo_id)
        if not staged_repo.is_dir():
            raise RuntimeError(f"Downloaded Hugging Face cache is missing: {staged_repo}")

        run_beam("cp", str(staged_repo), f"beam://{model.volume}/{repo_cache_name}")

        if not snapshot_is_complete(model.volume, snapshot_path, expected_files):
            raise RuntimeError(
                f"{model.name}: Beam volume does not contain the complete snapshot after upload"
            )

    print(f"{model.name}: verified complete snapshot in {model.volume}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    models = declared_models()
    if not models:
        raise RuntimeError(f"No MODEL_CACHES declarations found under {WORKERS_ROOT}")

    volumes = existing_volumes() if not args.dry_run else set()
    for model in models:
        if args.dry_run:
            print(f"{model.name}: {model.repo_id} -> {model.volume} ({model.cache_path})")
        else:
            seed_model(model, volumes)


if __name__ == "__main__":
    main()
