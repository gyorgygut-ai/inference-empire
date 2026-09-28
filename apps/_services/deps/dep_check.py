"""Dep parity pre-flight: worker file is the single source of truth."""
from __future__ import annotations

import ast
import shutil
import sys
from importlib import metadata
from pathlib import Path

TORCH_SHIM = "dist.is_available = lambda: False"


def extract_pins(worker_path):
    """Pin strings via AST (no import, no SDK): @Endpoint(dependencies=[...]),
    .add_python_packages([...]), .pip_install(...)."""
    tree = ast.parse(Path(worker_path).read_text())
    pins = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                pins += [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "add_python_packages" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.List):
                pins += [e.value for e in arg.elts if isinstance(e, ast.Constant)]
        if isinstance(func, ast.Attribute) and func.attr == "pip_install":
            pins += [a.value for a in node.args if isinstance(a, ast.Constant)]
    return pins


def _name(pin):
    for sep in ("[", "==", ">=", "<=", "!=", ">", "<", "~="):
        pin = pin.split(sep)[0]
    return pin.strip()


def check_installed(pins):
    """Raise the exact mismatch: non-== pin, missing dist, or drifted version."""
    for pin in pins:
        if "==" not in pin:
            raise RuntimeError(f"not an exact pin: {pin}")
        want = pin.split("==", 1)[1].strip()
        try:
            got = metadata.version(_name(pin))
        except metadata.PackageNotFoundError:
            raise RuntimeError(f"not installed: {pin}") from None
        if got != want:
            raise RuntimeError(f"drift: {pin} installed={got}")


def check_worker(worker_path):
    check_installed(extract_pins(worker_path))
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(f"python==3.11 required, running {sys.version.split()[0]}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not on PATH")
    if TORCH_SHIM not in Path(worker_path).read_text():
        raise RuntimeError(f"torch shim missing in {worker_path}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        check_worker(path)
        print(f"parity ok: {path}")
