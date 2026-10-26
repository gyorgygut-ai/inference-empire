"""Provider contract of the entry files, asserted from source, no network.

Level 1 runs the entry files through their ``__main__`` guards, which never
touches the provider CLI. These checks cover exactly what the CLI enforces and
what a local run therefore cannot catch: deployable handler name, no GPU, and
the request ceiling.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEAM_ENTRY = ROOT / "worker_beam_asgi_voice.py"
MODAL_ENTRY = ROOT / "worker_modal_cls_voice.py"
APP_NAME = "voice-proof-worker"
BANNED_MODEL_CALLS = ("from_pretrained", "load_model", "AutoModel", "pipeline(")


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def _decorator_kwargs(path: Path, label: str) -> dict[str, ast.expr]:
    for node in ast.walk(_tree(path)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == label:
                return {kw.arg: kw.value for kw in decorator.keywords if kw.arg}
    raise AssertionError(f"@{label}(...) not found in {path.name}")


def _constant(node: ast.expr | None) -> object:
    return node.value if isinstance(node, ast.Constant) else None


def test_beam_handler_declares_a_deployable_name() -> None:
    kwargs = _decorator_kwargs(BEAM_ENTRY, "asgi")

    assert _constant(kwargs.get("name")) == APP_NAME


def test_beam_is_cpu_only_and_honours_the_request_ceiling() -> None:
    kwargs = _decorator_kwargs(BEAM_ENTRY, "asgi")

    assert _constant(kwargs.get("gpu")) is None
    assert _constant(kwargs.get("timeout")) == 600
    assert _constant(kwargs.get("keep_warm_seconds")) == 600


def test_modal_app_declares_the_name_and_runs_without_gpu() -> None:
    app_calls = [
        node
        for node in ast.walk(_tree(MODAL_ENTRY))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "App"
    ]

    assert app_calls, "modal.App(...) not found"
    assert _constant(app_calls[0].args[0]) == APP_NAME
    assert _constant(_decorator_kwargs(MODAL_ENTRY, "cls").get("gpu")) is None


def test_entry_files_load_no_models() -> None:
    for path in (BEAM_ENTRY, MODAL_ENTRY):
        text = path.read_text()

        assert [call for call in BANNED_MODEL_CALLS if call in text] == []
