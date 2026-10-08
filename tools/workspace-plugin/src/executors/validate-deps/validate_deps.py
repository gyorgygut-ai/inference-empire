"""Print a worker family's IMAGE_PIP_DEPS, one per line. No model import.

Usage: validate_deps.py <family>
Loads packages/<family>/shared.py by file location (mirrors the old inline
gate) so heavy provider deps never import.
"""
from __future__ import annotations

import glob
import importlib.util
import os
import sys


def main() -> int:
    sys.path.insert(0, os.getcwd())
    family = sys.argv[1]
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
