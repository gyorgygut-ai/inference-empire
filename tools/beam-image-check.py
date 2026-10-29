"""Run in the actual Beam image, without the repository on Python's import path."""
from __future__ import annotations

import importlib
import importlib.metadata
import json
from pathlib import Path

from packaging.requirements import Requirement


def check(root: Path) -> None:
    config = json.loads((root / "image-check.json").read_text())
    requirements = (root / "requirements.txt").read_text().replace("\\\n", "")
    versions = dict(config["local"])
    for line in requirements.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        requirement = Requirement(line.split("--hash=", 1)[0].strip())
        if requirement.marker is None or requirement.marker.evaluate():
            version = importlib.metadata.version(requirement.name)
            if not requirement.specifier.contains(version):
                raise RuntimeError(f"{requirement.name}: installed {version}, expected {requirement.specifier}")
            versions[requirement.name] = version
    for name, version in config["local"].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"Local wheel version mismatch: {name}")
    for name in config["imports"]:
        module, _, attribute = name.partition(":")
        imported = importlib.import_module(module)
        if attribute:
            getattr(imported, attribute)
    print(json.dumps({"status": "PASS", "versions": versions}, sort_keys=True), flush=True)


if __name__ == "__main__":
    check(Path(__file__).resolve().parent)
