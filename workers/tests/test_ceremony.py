"""Ceremony test: decorators, contracts, and module imports.

No behavior, no mocks — asserts the shipping surface stays intact:
every worker module imports, every provider decorator carries its
identity/scheduling params, and every contract JSON matches its shared
pydantic model (title + required keys). Voice contracts assert their
output event-type enums separately.
"""

import ast
import importlib
import json
from pathlib import Path

WORKERS = Path(__file__).parent.parent

# All 22 worker modules must import cleanly (provider SDKs + shared code).
WORKER_MODULES = [
    "workers.flux2.worker_flash_cls_flux2_klein9b",
    "workers.flux2.worker_beam_tq_flux2_klein9b",
    "workers.flux2.worker_modal_cls_flux2_klein9b",
    "workers.krea2.worker_flash_cls_krea2_ref2img",
    "workers.krea2.worker_beam_tq_krea2_ref2img",
    "workers.krea2.worker_modal_cls_krea2_ref2img",
    "workers.h3.worker_flash_cls_minimax_h3_fl2va",
    "workers.h3.worker_beam_tq_minimax_h3_fl2va",
    "workers.h3.worker_modal_cls_minimax_h3_fl2va",
    "workers.h3.worker_flash_cls_minimax_h3_ref2va",
    "workers.h3.worker_beam_tq_minimax_h3_ref2va",
    "workers.h3.worker_modal_cls_minimax_h3_ref2va",
    "workers.h3.worker_flash_cls_minimax_h3_comfy",
    "workers.h3.worker_flash_pre_minimax_h3_ref2va_comfy",
    "workers.h3.worker_beam_tq_minimax_h3_ref2va_comfy",
    "workers.vision.worker_flash_cls_small_vision",
    "workers.vision.worker_beam_eq_small_vision",
    "workers.vision.worker_modal_cls_small_vision",
    "workers.voice.worker_beam_asgi_realtime_voice_openvoice",
    "workers.voice.worker_beam_asgi_realtime_voice_chatterbox",
    "workers.voice.worker_beam_asgi_realtime_voice_qwen",
    "workers.voice.worker_modal_cls_voice_chat",
]

# contract file -> (shared module, Input name, Output name)
CONTRACT_MODELS = {
    "workers/flux2/contracts/flux2_klein9b.json": (
        "workers.flux2.generate_flux2_klein9b",
        "Flux2Klein9bInput",
        "Flux2Klein9bOutput",
    ),
    "workers/krea2/contracts/krea2_ref2img.json": (
        "workers.krea2.generate_krea2_ref2img",
        "Krea2Ref2ImgInput",
        "Krea2Ref2ImgOutput",
    ),
    "workers/h3/contracts/minimax_h3_fl2va.json": (
        "workers.h3.generate_minimax_h3_fl2va",
        "MiniMaxH3Fl2VAInput",
        "MiniMaxH3Fl2VAOutput",
    ),
    "workers/h3/contracts/minimax_h3_ref2va.json": (
        "workers.h3.generate_minimax_h3_ref2va",
        "MiniMaxH3Ref2VAInput",
        "MiniMaxH3Ref2VAOutput",
    ),
    "workers/h3/contracts/minimax_h3_comfy.json": (
        "workers.h3.generate_minimax_h3_comfy",
        "MiniMaxH3ComfyInput",
        "MiniMaxH3ComfyOutput",
    ),
    "workers/h3/contracts/minimax_h3_ref2va_comfy.json": (
        "workers.h3.generate_minimax_h3_ref2va_comfy",
        "MiniMaxH3Ref2VAComfyInput",
        "MiniMaxH3Ref2VAComfyOutput",
    ),
    "workers/vision/contracts/small_vision.json": (
        "workers.vision.analyze_small_vision",
        "SmallVisionInput",
        "SmallVisionOutput",
    ),
}


def _func_name(func):
    if isinstance(func, ast.Name):
        return func.id
    return getattr(func, "attr", "")


def _safe_eval(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return "<expr>"  # variable reference (e.g. image=image): present, not empty


def _decorator_kwargs(tree, func_name):
    """All @func_name(...) keyword args across a module AST."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and _func_name(dec.func) == func_name:
                    found.append({kw.arg: _safe_eval(kw.value) for kw in dec.keywords})
        elif isinstance(node, ast.Call) and _func_name(node.func) == func_name:
            # modal.App("name") call sites (also catches decorator Calls
            # re-visited by the walk — keywords included so they merge).
            found.append(
                {"_args": [_safe_eval(a) for a in node.args],
                 **{kw.arg: _safe_eval(kw.value) for kw in node.keywords}}
            )
    return found


def _module_path(name):
    return WORKERS.parent / (name.replace(".", "/") + ".py")


def test_all_worker_modules_import():
    for name in WORKER_MODULES:
        importlib.import_module(name)


def test_flash_decorators_carry_identity_and_gpu():
    for name in WORKER_MODULES:
        if "flash_cls" not in name and "flash_pre" not in name:
            continue
        tree = ast.parse(_module_path(name).read_text())
        eps = _decorator_kwargs(tree, "Endpoint")
        assert eps, f"{name}: no @Endpoint found"
        for kw in eps:
            if "name" in kw:
                assert kw["name"], f"{name}: empty Endpoint name"
            if "gpu" in kw:
                assert kw["gpu"], f"{name}: empty Endpoint gpu"


def test_beam_decorators_carry_names():
    for name in WORKER_MODULES:
        if ".worker_beam_" not in name:
            continue
        tree = ast.parse(_module_path(name).read_text())
        seen = 0
        for func in ("task_queue", "endpoint", "asgi"):
            for kw in _decorator_kwargs(tree, func):
                assert kw.get("name"), f"{name}: @{func} without name"
                seen += 1
        assert seen, f"{name}: no beam decorator found"


def test_modal_apps_and_cls_carry_scheduling():
    for name in WORKER_MODULES:
        if ".worker_modal_" not in name:
            continue
        tree = ast.parse(_module_path(name).read_text())
        apps = _decorator_kwargs(tree, "App")
        assert apps and all(a["_args"] and a["_args"][0] for a in apps), (
            f"{name}: modal.App without name"
        )
        for kw in _decorator_kwargs(tree, "cls"):
            assert kw.get("gpu"), f"{name}: @app.cls without gpu"
            assert kw.get("timeout"), f"{name}: @app.cls without timeout"
            assert kw.get("image") is not None, f"{name}: @app.cls without image"


def test_contracts_match_shared_models():
    for rel, (module_name, input_name, output_name) in CONTRACT_MODELS.items():
        contract = json.loads((WORKERS.parent / rel).read_text())
        mod = importlib.import_module(module_name)
        for side, model_name in (("input", input_name), ("output", output_name)):
            model = getattr(mod, model_name)
            assert contract[side]["title"] == model.__name__, rel
            required = {
                fname for fname, f in model.model_fields.items() if f.is_required()
            }
            assert set(contract[side]["required"]) == required, f"{rel}:{side}"


def test_voice_contract_event_enums():
    for rel in sorted((WORKERS / "voice" / "contracts").glob("realtime_voice_*.json")):
        if rel.name == "realtime_voice_chatterbox.json":
            # REST TTS, not realtime events: audio payload contract instead.
            contract = json.loads(rel.read_text())
            assert set(contract["output"]["required"]) == {"audio", "content_type"}
            continue
        contract = json.loads(rel.read_text())
        enum = contract["output"]["properties"]["type"].get("enum", [])
        assert enum, f"{rel.name}: empty output event enum"
        assert "error" in enum, f"{rel.name}: enum missing 'error'"
