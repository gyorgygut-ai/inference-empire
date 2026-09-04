# Plan: Restructure services/ into packages + local pip package

## Goal
Make `services/storage` a proper pip-installable package so workers deployed to Modal/Beam can import `RealR2Storage` without the full `services/` directory being on the filesystem.

## Target Structure
```
services/
├── __init__.py
├── storage/
│   ├── __init__.py
│   ├── storage.py      # Storage ABC (5 lines)
│   ├── real_r2.py      # RealR2Storage (36 lines)
│   └── fake_r2.py      # FakeR2Storage (18 lines)
├── platform/
│   ├── __init__.py
│   ├── beam_platform.py
│   ├── beam_platform_fake.py
│   ├── modal_platform.py
│   ├── modal_platform_fake.py
│   ├── flash_platform.py
│   └── flash_platform_fake.py
├── runner/
│   ├── __init__.py
│   ├── beam_runner.py
│   ├── modal_runner.py
│   └── flash_runner.py
└── tests/
    └── conftest.py
```

## Steps

### 1. Create directories and __init__.py files
```bash
mkdir services/storage services/platform services/runner
touch services/storage/__init__.py services/platform/__init__.py services/runner/__init__.py
```

### 2. Move files
- `services/storage.py` → `services/storage/storage.py`
- `services/real_r2.py` → `services/storage/real_r2.py`
- `services/fake_r2.py` → `services/storage/fake_r2.py`
- `services/*_platform*.py` → `services/platform/`
- `services/*_runner.py` → `services/runner/`
- Remove original files

### 3. Update __init__.py files for re-exports
```python
# services/__init__.py — keep empty or add:
from services.storage import Storage

# services/storage/__init__.py
from services.storage.storage import Storage
from services.storage.real_r2 import RealR2Storage
from services.storage.fake_r2 import FakeR2Storage

# services/platform/__init__.py
from services.platform.beam_platform import RealBeamPlatform
from services.platform.beam_platform_fake import FakeBeamPlatform
from services.platform.modal_platform import RealModalPlatform
from services.platform.modal_platform_fake import FakeModalPlatform
from services.platform.flash_platform import RealFlashPlatform
from services.platform.flash_platform_fake import FakeFlashPlatform

# services/runner/__init__.py
from services.runner.beam_runner import DirectAsyncRunner
from services.runner.modal_runner import DirectAsyncRunner
from services.runner.flash_runner import DirectSyncRunner
```

### 4. Update pyproject.toml
Add:
```toml
[tool.setuptools.packages.find]
where = ["services"]
include = ["storage*", "platform*", "runner*"]
```
Add `boto3` to `[project.optional-dependencies]` under a `storage` group.

### 5. Update imports in all worker files
Change `from services.real_r2 import RealR2Storage` → `from services.storage.real_r2 import RealR2Storage`

Affected files (~20):
- flux2: worker_flash_cls_flux2_klein9b.py, worker_modal_cls_flux2_klein9b.py, worker_beam_tq_flux2_klein9b.py
- krea2: worker_flash_cls_krea2_ref2img.py, worker_modal_cls_krea2_ref2img.py, worker_beam_tq_krea2_ref2img.py
- h3: all 9 workers
- vision: worker_flash_cls_small_vision.py, worker_modal_cls_small_vision.py, worker_beam_eq_small_vision.py
- voice: worker_beam_asgi_realtime_voice_chatterbox.py, worker_beam_asgi_realtime_voice_openvoice.py, worker_beam_asgi_realtime_voice_qwen.py, worker_modal_cls_voice_chat.py

## Verification
- Run `python -m pytest --target fake` — all tests pass
- Verify `pip install -e .` still works