"""Optionally seed available reference voices into the persistent Beam volume."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[2]
REFERENCE_SOURCE = ROOT / "references"
VOLUME = "hf-cache"


def run(*command: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["uv", "run", "--locked", "--project", str(WORKSPACE_ROOT), "beam", *command],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode:
        output = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(command)} failed: {output}")
    return result


def main() -> None:
    available = sorted(
        source for source in REFERENCE_SOURCE.glob("*.wav")
        if source.is_file() and source.stat().st_size
    )

    if not available:
        print("No local reference voice files; skipping optional Beam volume seed.")
        return

    with tempfile.TemporaryDirectory(prefix="voice-reference-seed-") as temporary:
        staged = Path(temporary) / "reference_voices"
        staged.mkdir()
        for source in available:
            shutil.copy2(source, staged / source.name)
        manifest = REFERENCE_SOURCE / "voices.json"
        if manifest.is_file():
            shutil.copy2(manifest, staged / manifest.name)
        run("cp", str(staged), f"beam://{VOLUME}/reference_voices")
    print(f"Seeded {len(available)} reference voice(s) into Beam volume {VOLUME}/reference_voices.")


if __name__ == "__main__":
    main()
