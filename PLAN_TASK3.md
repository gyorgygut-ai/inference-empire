# Plan: Worker run_generate extraction

## Goal
Extract the core `run_generate(pipe, storage, **kwargs)` logic from each worker into a shared file so each worker becomes a thin wrapper (~30-60 lines, down from ~200-350).

## Scope — 6 shared files (one per model variant)

### 1. flux2/worker_generate_flux2_klein9b.py
- **Content**: `run_generate(pipe, storage, prompt, height, width, guidance_scale, num_inference_steps, seed, input_image, reference_images)`
- **Logic**: `_prepare_image` (inline or called) → build `pipe_kwargs` → optional seed → call `pipe(**pipe_kwargs)` → save PNG to BytesIO → `storage.put()` → `storage.presigned_url()` → return `{"artifact": {"presigned_url": url}}`

### 2. krea2/worker_generate_krea2_ref2img.py
- **Content**: `run_generate(pipe, storage, prompt, reference_image, height, width, num_inference_steps, guidance_scale, seed, lora_scale, face_crop)`
- **Logic**: `_decode_image`, `_face_crop` (inline) → build kwargs → call pipe → save PNG → R2 → return

### 3. h3/worker_generate_minimax_h3_ref2va.py
- **Content**: `run_generate(pipe, storage, prompt, ref_images, ref_videos, ref_video_audios, ref_audios, width, height, length, steps, seed)`
- **Logic**: `_read_image`, `_read_video`, `_read_audio`, `_build_references` (inline) → build kwargs → call pipe → `write_video_audio` → R2 → return

### 4. h3/worker_generate_minimax_h3_fl2va.py
- **Content**: `run_generate(pipe, storage, prompt, first_frame, last_frame, width, height, length, steps, seed)`
- **Logic**: `_decode_image` (inline) → keyframe logic (`first_frame`/`last_frame` → `keyframes`/`keyframe_indices`) → call pipe → R2 → return

### 5. h3/worker_generate_minimax_h3_comfy.py
- **Content**: `run_generate(pipe, storage, prompt, first_frame, last_frame, width, height, length, steps, seed)`
- **Logic**: `_build_workflow`, `_build_images`, ComfyUI HTTP poll (inline) → download video → R2 → return

### 6. h3/worker_generate_minimax_h3_ref2va_comfy.py
- **Content**: `run_generate(pipe, storage, prompt, ref_images, ref_videos, ref_video_audios, ref_audios, ...)`
- **Logic**: Same as comfy + ref2va media parsing → ComfyUI workflow → poll → R2 → return

## Worker file template (before → after)

### Before (flux2 flash, 238 lines):
```python
class FluxKleinWorker:
    Input = Flux2Klein9bInput  # 12 lines inline
    
    def _prepare_image(self, base64_str):  # 8 lines
        ...
    
    def _run_generate(self, ...):  # 60+ lines
        # build kwargs
        # call pipe
        # save to R2
        ...
    
    def generate(self, prompt, height, ...):
        # parse inputs
        # call _run_generate
        # handle errors
        ...
```

### After (~40 lines):
```python
from services.storage.real_r2 import RealR2Storage
from worker_generate_flux2_klein9b import run_generate

@Endpoint(
    name="flux2-klein9b-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={"SDNQ_USE_TRITON_MM": "0", "HF_TOKEN": ..., ...},
    dependencies=["torch==2.9.1", "diffusers", "transformers>=5.0,<6", ...],
)
class FluxKleinWorker:
    Input = Flux2Klein9bInput  # inline only
    
    def __init__(self, pipe=None, storage=None):
        self.Input = Flux2Klein9bInput
        self.storage = storage or RealR2Storage()
        if pipe is not None:
            self.pipe = pipe
        else:
            self.pipe = load_pipeline()
    
    def generate(self, prompt, height=512, width=512, guidance_scale=1.0,
                 num_inference_steps=4, seed=None, input_image=None,
                 reference_images=[]):
        from worker_generate_flux2_klein9b import run_generate
        try:
            return run_generate(self.pipe, self.storage, prompt, height, width,
                                guidance_scale, num_inference_steps, seed,
                                input_image, reference_images)
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
```

## Affected files

### New files (6):
- `flux2/worker_generate_flux2_klein9b.py`
- `krea2/worker_generate_krea2_ref2img.py`
- `h3/worker_generate_minimax_h3_ref2va.py`
- `h3/worker_generate_minimax_h3_fl2va.py`
- `h3/worker_generate_minimax_h3_comfy.py`
- `h3/worker_generate_minimax_h3_ref2va_comfy.py`

### Modified files (~20):
- `flux2/`: worker_flash_cls_flux2_klein9b.py, worker_modal_cls_flux2_klein9b.py, worker_beam_tq_flux2_klein9b.py
- `krea2/`: worker_flash_cls_krea2_ref2img.py, worker_modal_cls_krea2_ref2img.py, worker_beam_tq_krea2_ref2img.py
- `h3/`: all 9 workers
- `vision/`: worker_flash_cls_small_vision.py, worker_modal_cls_small_vision.py, worker_beam_eq_small_vision.py
- `voice/`: worker_beam_asgi_realtime_voice_chatterbox.py, worker_beam_asgi_realtime_voice_openvoice.py, worker_beam_asgi_realtime_voice_qwen.py, worker_modal_cls_voice_chat.py

## Line count impact
| Service | Before (total) | After (shared + workers) | Saved |
|---------|---------------|-------------------------|-------|
| flux2 | ~683 | ~120 | ~560 |
| krea2 | ~680 | ~140 | ~540 |
| h3 | ~3150 | ~500 | ~2650 |
| **Total** | **~4500** | **~760** | **~3740** |

## Verification
- Run `python -m pytest --target fake` — all tests pass
- Each worker file is importable
- `run_generate` returns same output structure: `{"artifact": {"presigned_url": "https://..."}}`