import json
import re
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = PROJECT_ROOT / "references"
VOLUME_NAME = "worker-voice-reference-voices"


def contains_volume(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("name") == VOLUME_NAME:
            return True
        return any(contains_volume(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_volume(item) for item in value)
    return False


def contains_references_dir(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("path", "").rstrip("/") == "references" and value.get(
            "is_dir"
        ):
            return True
        return any(contains_references_dir(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_references_dir(item) for item in value)
    return False


def main() -> None:
    if not REFERENCES_DIR.is_dir():
        return

    listing = subprocess.run(
        ["beam", "volume", "list", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    volumes = json.loads(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", listing.stdout))
    volume_exists = contains_volume(volumes)
    if not volume_exists:
        subprocess.run(["beam", "volume", "create", VOLUME_NAME], check=True)
    else:
        listing = subprocess.run(
            ["beam", "ls", VOLUME_NAME, "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
        )
        contents = json.loads(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", listing.stdout))
        if contains_references_dir(contents):
            print(f"{VOLUME_NAME}/references already exists; skipping upload")
            return

    subprocess.run(
        ["beam", "cp", str(REFERENCES_DIR), f"beam://{VOLUME_NAME}/"],
        check=True,
    )


if __name__ == "__main__":
    main()
