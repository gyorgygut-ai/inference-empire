# Plan: Fix Modal Comfy Workers (h3-comfy + h3-ref2va-comfy)

## Root Cause
`ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130` is too large for Modal's image builder → `external shut-down` during `unpacking rootfs`. Both comfy workers fail because they share this registry image.

## Solution
Replace `from_registry()` with `modal.Image.debian_slim()` + git-clone ComfyUI + pip install + `@modal.enter()` model download into a `modal.Volume` cache.

## Critical Constraint
`_shared_minimax_h3_comfy.py` and `_shared_minimax_h3_ref2va_comfy.py` are shared across Flash, Beam, and Modal. **Zero modifications to shared files.** All new deps and download logic live inline in the two Modal worker files only.

## Investigation Results

### 1. Model file source
`Comfy-Org/MiniMax-H3` on HuggingFace. Files go into ComfyUI's `models/` subdirectories:
- **fl2va**: `diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors`, `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, `vae/minimax_h3_video_vae_fp16.safetensors`, `vae/minimax_h3_audio_vae_fp32.safetensors`
- **ref2va**: `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors`, same text_encoder and VAE files

### 2. ComfyUI custom nodes
`MiniMaxH3ImageToVideo` and `MiniMaxH3ReferenceToVideo` are **native ComfyUI nodes** built into ComfyUI >=0.30.0. No custom node repo needed.

### 3. ComfyUI install
Standard git clone + `pip install -r requirements.txt`.

## Files Changed (4 files)

### `workers/h3/worker_modal_cls_minimax_h3_comfy.py` — full rewrite
- Drop `from_registry()`
- New image:
  ```python
  CACHE_PATH = "./hf-cache"
  MODAL_IMAGE_PIP_DEPS = [
      "comfyui",
      "huggingface-hub==1.29.0",
      "hf_transfer==0.1.9",
      "boto3==1.43.83",
      "pydantic==2.13.5",
  ]
  image = (
      modal.Image.debian_slim(python_version="3.11")
      .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
      .run_commands("git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /ComfyUI")
      .workdir("/ComfyUI")
      .run_commands("pip install -r requirements.txt")
      .pip_install(*MODAL_IMAGE_PIP_DEPS)
      .env({
          "HF_HOME": "/root/.cache/huggingface",
          "HF_HUB_ENABLE_HF_TRANSFER": "1",
          "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
          "DIFFSYNTH_MODEL_BASE_PATH": "/root/.cache/huggingface/diffsynth",
      })
      .add_local_python_source("workers.services", "workers.h3")
  )
  ```
- Add `hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)` to `@app.cls`
- Inline `download_models(cache_dir)` using `huggingface_hub.hf_hub_download(repo_id="Comfy-Org/MiniMax-H3", ...)` into `<cache_dir>/ComfyUI/models/{diffusion_models,text_encoders,vae}/`
- `@modal.enter()` calls `download_models()` then starts ComfyUI subprocess with `--models-dir {cache_dir}/ComfyUI/models`
- `_start_comfy()` signature changes to accept `models_dir`

### `workers/h3/worker_modal_cls_minimax_h3_ref2va_comfy.py` — same treatment
- Identical image/deps structure
- `download_models()` with ref2va filenames

### `workers/h3/_shared_minimax_h3_comfy.py` — **zero changes**
### `workers/h3/_shared_minimax_h3_ref2va_comfy.py` — **zero changes**

## Pre-deploy Gates
Run per-worker (deps are inline, not in shared code):
```bash
# h3-comfy
uv run python -c "import sys; sys.path.insert(0, 'workers/h3'); from worker_modal_cls_minimax_h3_comfy import MODAL_IMAGE_PIP_DEPS; print('\n'.join(MODAL_IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
# h3-ref2va-comfy
uv run python -c "import sys; sys.path.insert(0, 'workers/h3'); from worker_modal_cls_minimax_h3_ref2va_comfy import MODAL_IMAGE_PIP_DEPS; print('\n'.join(MODAL_IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
```

## Execution Order
1. Pre-deploy gates for both comfy workers
2. Deploy both Modal comfy workers
3. Run `.spawn()` generation + save artifacts

## Residual Risk
- ComfyUI git clone + pip install adds ~2-3 min to image build (acceptable)
- Model download on first cold start adds ~1-2 min (cached by volume)
- Native ComfyUI nodes confirmed present in >=0.30.0
