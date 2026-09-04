# Plan: Conftest refactoring — replace if/elif factories with DI registry

## Goal
Replace 500+ lines of conftest.py with a clean, data-driven DI harness (~150 lines). Keep platform/runner abstraction boundaries. Eliminate global mutable state and 4 useless proxy classes.

## Current problems
1. **12+ `_make_*` factory functions** — one per service × platform × variant combo
2. **If/elif routing** — `_detect_service`, `_detect_h3_variant`, `_get_worker_factory` use substring matching on filenames
3. **4 proxy classes** — 3 are identical pass-throughs; only `BeamWorkerProxy` does anything special
4. **Global mutable state** — `_mock_model` with `_should_fail` toggled by test name parsing
5. **No IoC** — harness constructs everything inline instead of delegating to a registry

## New architecture

### 1. WorkerRegistry (IoC container)
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

### 2. Unified WorkerProxy (replaces 4 classes)
```python
class WorkerProxy:
    def __init__(self, worker, is_beam_fn=False):
        self._worker = worker
        self._is_beam_fn = is_beam_fn

    def generate(self, **inputs):
        if self._is_beam_fn:
            class _FakeContext:
                on_start_value = (None, None, None)
            return self._worker(_FakeContext(), **inputs)
        return self._worker.generate(**inputs)
```

### 3. Factory resolution
```python
def _resolve_platform(test_path, test_file):
    if "beam" in test_file: return "beam"
    if "modal" in test_file: return "modal"
    return "flash"

def _resolve_variant(test_file, service):
    if service != "h3": return "default"
    if "fl2va" in test_file: return "fl2va"
    if "comfy_pre" in test_file: return "comfy_pre"
    if "comfy" in test_file: return "comfy"
    return "ref2va"

def _detect_service(test_path):
    for svc in ["vision", "flux2", "krea2", "h3"]:
        if f"/{svc}/" in test_path:
            return svc
    return None

class WorkerFactory:
    def __init__(self):
        self._registry = WORKER_REGISTRY

    def make(self, service, platform_name, variant, storage):
        key = (service, platform_name, variant) if service == "h3" else (service, platform_name)
        entry = self._registry[key]

        module = importlib.import_module(entry["module"])
        if "class" in entry:
            cls = getattr(module, entry["class"])
            worker = cls(pipe=_FakePipe(), storage=storage)
            return WorkerProxy(worker)
        else:
            fn = getattr(module, entry["fn"])
            return WorkerProxy(fn, is_beam_fn=True)
```

### 4. Per-test mock state (DI)
```python
class MockModel:
    def __init__(self):
        self._should_fail = False

    def generate(self, **kw):
        if self._should_fail:
            raise RuntimeError("inference failed")
        return [[1, 2, 3, 4, 5]]

class MockProcessor:
    def apply_chat_template(self, *a, **kw): return "fake template"
    def __call__(self, *a, **kw):
        class FakeInputs(dict):
            input_ids = type("obj", (object,), {"shape": [1, 10]})()
            def to(self, device): return self
        return FakeInputs()
    def decode(self, *a, **kw):
        return '{"classification": "landscape_0p", "subjects": ["sky"], "description": "blue sky"}'

@pytest.fixture
def mock_model():
    return MockModel()

@pytest.fixture(autouse=True)
def _reset_mock(mock_model):
    mock_model._should_fail = False
    yield
```

### 5. Keep platform/runner fixtures (unchanged logic)
- `storage` fixture — returns RealR2Storage or FakeR2Storage based on `--target`
- `platform` fixture — uses WorkerFactory to create worker, returns Real*Platform or Fake*Platform
- `runner` fixture — returns DirectSyncRunner or DirectAsyncRunner based on test file
- `lifecycle` fixture — calls platform.deploy()/undeploy()

## What gets removed
- 12+ `_make_*` factory functions
- 4 proxy classes → 1 unified `WorkerProxy`
- Global `_mock_model` and `_mock_processor`
- `_detect_h3_variant` → moved into `WorkerFactory` or inlined
- `_get_worker_factory` → replaced by `WorkerFactory.make()`

## Line count impact
- Before: ~504 lines in conftest.py
- After: ~150 lines
- Saved: ~354 lines

## Verification
- `python -m pytest --target fake` — all tests pass
- `python -m pytest --target live` — workers deploy and tests pass
- Each service (vision, flux2, krea2, h3) × each platform (flash, modal, beam) works