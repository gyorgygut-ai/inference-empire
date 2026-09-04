# Plan for Testing Harness Redesign (PLAN_TESTING_V2.md)

## Problem Statement
The current test harness (`services/tests/conftest.py`) spans over 500 lines and suffers from severe anti-patterns:
1. **If/Else Hell**: String detection based on file paths (`_detect_service`, `_detect_h3_variant`) coupled with 12+ redundant `_make_*` factory functions.
2. **Useless Proxy Explosion**: 4 separate proxy classes (`BeamWorkerProxy`, `VisionFlashWorkerProxy`, `VisionBeamWorkerProxy`, `VisionModalWorkerProxy`), most of which are duplicate pass-throughs.
3. **Global Mutable State**: `_mock_model` is a module-level mutable object, and `_configure_inference_mock` uses magic test-name parsing (`"failure"` in test name) to flip state.
4. **Lack of IoC**: The test harness hardcodes all worker constructions rather than using a data-driven container/registry.

---

## Redesign Goals (DI & IoC Principles)
1. **Data-Driven Registry**: Replace the 12+ factory functions with a single `WORKER_REGISTRY` dict mapping `(service, platform, variant)` to module/class paths.
2. **Unified Proxy**: Condense 4 proxy classes into a single `WorkerProxy` wrapper.
3. **Per-Test Mock State**: Remove the global mutable model. Replace it with a `mock_model` fixture with per-test lifecycle isolation.
4. **Keep Abstraction Boundaries**: Retain `platform` and `runner` as lightweight abstraction boundaries (real vs fake behavior).

---

## Implementation Details

### 1. Worker Registry (IoC Container)
```python
WORKER_REGISTRY = {
    ("vision", "flash"): {"class": "Qwen2VLVisionWorker", "module": "vision.worker_flash_cls_small_vision"},
    ("vision", "beam"): {"fn": "analyze", "module": "vision.worker_beam_eq_small_vision"},
    ("vision", "modal"): {"class": "SmallVisionWorker", "module": "vision.worker_modal_cls_small_vision"},
    ("flux2", "flash"): {"class": "FluxKleinWorker", "module": "flux2.worker_flash_cls_flux2_klein9b"},
    ("flux2", "beam"): {"fn": "generate", "module": "flux2.worker_beam_tq_flux2_klein9b"},
    ("flux2", "modal"): {"class": "FluxKleinWorker", "module": "flux2.worker_modal_cls_flux2_klein9b"},
    ("krea2", "flash"): {"class": "Krea2Ref2ImgWorker", "module": "krea2.worker_flash_cls_krea2_ref2img"},
    ("krea2", "beam"): {"fn": "generate", "module": "krea2.worker_beam_tq_krea2_ref2img"},
    ("krea2", "modal"): {"class": "Krea2Ref2ImgWorker", "module": "krea2.worker_modal_cls_krea2_ref2img"},
    ("h3", "flash", "ref2va"): {"class": "MiniMaxH3Ref2VAWorker", "module": "h3.worker_flash_cls_minimax_h3_ref2va"},
    ("h3", "flash", "fl2va"): {"class": "MiniMaxH3Fl2VAWorker", "module": "h3.worker_flash_cls_minimax_h3_fl2va"},
    ("h3", "flash", "comfy"): {"class": "MiniMaxH3ComfyWorker", "module": "h3.worker_flash_cls_minimax_h3_comfy"},
    ("h3", "flash", "comfy_pre"): {"class": "MiniMaxH3Ref2VAComfyWorker", "module": "h3.worker_flash_pre_minimax_h3_ref2va_comfy"},
    ("h3", "beam", "ref2va"): {"fn": "generate", "module": "h3.worker_beam_tq_minimax_h3_ref2va"},
    ("h3", "beam", "fl2va"): {"fn": "generate", "module": "h3.worker_beam_tq_minimax_h3_fl2va"},
    ("h3", "beam", "comfy"): {"fn": "generate", "module": "h3.worker_beam_tq_minimax_h3_ref2va_comfy"},
    ("h3", "modal", "ref2va"): {"class": "MiniMaxH3Ref2VAWorker", "module": "h3.worker_modal_cls_minimax_h3_ref2va"},
    ("h3", "modal", "fl2va"): {"class": "MiniMaxH3Fl2VAWorker", "module": "h3.worker_modal_cls_minimax_h3_fl2va"},
}
```

### 2. Factory and DI Wiring
A single factory class resolves the entry from the registry, injects the fake pipe and storage, and wraps it in the unified proxy.

### 3. Per-Test Mock State
Remove global `_mock_model` state. Use a clean pytest fixture that resets failure flags per test execution.
