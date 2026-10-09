"""Print a worker family's IMAGE_PIP_DEPS, one per line. No model import.

Usage: validate_deps.py <family>
Loads packages/<family>/shared.py by file location (mirrors the old inline
gate) so heavy provider deps never import.

Also enforces worker thinness: apps/<family>/worker_*.py must not contain
duplicated platform mechanics (lock, env, volume, typing shims). Those live
in packages/shared_gpu. Violations go to stderr with exit 1; stdout stays
pure IMAGE_PIP_DEPS for the pip-compile pipe.
"""
from __future__ import annotations

import glob
import importlib.util
import os
import sys

# realtime_voice Beam intentionally declares its own models volume; every
# other worker file must use the shared_gpu helpers.
_THINNESS_BANNED = (
    "_INFERENCE_LOCK = threading.Lock()",
    '"HF_HOME"',
    "Volume(name=",
    "Volume.from_name",
    "TYPE_CHECKING",
)
_THINNESS_EXEMPT = {
    "apps/realtime_voice/worker_beam_asgi_realtime_voice_qwen.py": (
        '"HF_HOME"',
        "Volume(name=",
    ),
}


def _check_thinness(family: str) -> list[str]:
    violations = []
    for path in sorted(glob.glob(f"apps/{family}/worker_*.py")):
        with open(path) as fh:
            text = fh.read()
        exempt = _THINNESS_EXEMPT.get(path, ())
        for banned in _THINNESS_BANNED:
            if banned in exempt:
                continue
            if banned in text:
                violations.append(f"{path}: banned {banned!r}, use packages/shared_gpu")
    return violations


def main() -> int:
    sys.path.insert(0, os.getcwd())
    family = sys.argv[1]
    violations = _check_thinness(family)
    if violations:
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    paths = glob.glob(f"packages/{family}/shared.py")
    assert len(paths) == 1, f"expected one shared file for {family}: {paths}"
    spec = importlib.util.spec_from_file_location("m", paths[0])
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    print("\n".join(m.IMAGE_PIP_DEPS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
