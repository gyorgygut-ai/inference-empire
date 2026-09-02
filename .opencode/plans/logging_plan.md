# Plan: Standard Runtime Debug Logging for All Workers

## 1. Standard Log Format

Every worker gets a single-line `print()` call with this format:

```
[<TAG>] <message>  [duration: X.Xs]
```

- **TAG**: `INIT` | `REQ` | `GEN` | `R2` | `OK` | `ERR`
- **duration**: appended only to completion messages (`INIT`, `GEN`, `R2`, `OK`, `ERR`)
- **flush=True** on every print
- No `import logging` — use `print()` (consistent with existing voice worker patterns)

## 2. Log Points (same for every worker)

Every worker MUST log at exactly these 7 lifecycle points:

| # | Tag   | When                                         | Message template                                                    |
|---|-------|----------------------------------------------|---------------------------------------------------------------------|
| 1 | `INIT`| `__init__` / `@modal.enter()` / `on_start` starts | `[INIT] loading model <repo_or_name>`                              |
| 2 | `INIT`| Model loaded successfully                    | `[INIT] model loaded from <repo_or_name> in X.Xs`                  |
| 3 | `REQ` | Request received                             | `[REQ] prompt=<truncated_to_40>  seed=<seed_or_none>  files=<N>`   |
| 4 | `GEN` | Inference starts                             | `[GEN] starting inference prompt=<truncated_to_40>`                |
| 5 | `GEN` | Inference completes                          | `[GEN] inference done in X.Xs  shape=<WxH>`                        |
| 6 | `R2`  | Upload completes                             | `[R2] uploaded key=<prefix_xxx> url=<truncated_url_to_60>`         |
| 7 | `OK`  | Request completes successfully               | `[OK] completed in X.Xs`                                           |
| X | `ERR` | Any exception                                | `[ERR] <exception_type>: <message>`                                |

## 3. Implementation Strategy

Each worker gets a `START_TIME = time.time()` at the top of the file and `time.time()` at each log point.

### Flux2 workers (3 files)
- `flux2/worker_beam_tq_flux2_klein9b.py`
- `flux2/worker_modal_cls_flux2_klein9b.py`
- `flux2/worker_flash_cls_flux2_klein9b.py`

### Krea2 workers (3 files)
- `krea2/worker_beam_tq_krea2_ref2img.py`
- `krea2/worker_modal_cls_krea2_ref2img.py`
- `krea2/worker_flash_cls_krea2_ref2img.py`

### Vision workers (3 files)
- `vision/worker_beam_eq_small_vision.py`
- `vision/worker_modal_cls_small_vision.py`
- `vision/worker_flash_cls_small_vision.py`

### H3 workers (9 files)
- `h3/worker_beam_tq_minimax_h3_ref2va.py`
- `h3/worker_beam_tq_minimax_h3_fl2va.py`
- `h3/worker_beam_tq_minimax_h3_ref2va_comfy.py`
- `h3/worker_modal_cls_minimax_h3_ref2va.py`
- `h3/worker_modal_cls_minimax_h3_fl2va.py`
- `h3/worker_flash_cls_minimax_h3_ref2va.py`
- `h3/worker_flash_cls_minimax_h3_fl2va.py`
- `h3/worker_flash_cls_minimax_h3_comfy.py`
- `h3/worker_flash_pre_minimax_h3_ref2va_comfy.py`

### Voice workers (4 files — already partially logged)
- `voice/worker_beam_asgi_realtime_voice_qwen.py`
- `voice/worker_beam_asgi_realtime_voice_openvoice.py`
- `voice/worker_beam_asgi_realtime_voice_chatterbox.py`
- `voice/worker_modal_cls_voice_chat.py`

## 4. Worker-Specific Log Adaptations

### Image generation (flux2, krea2) — standard 7 points

```python
import time
START_TIME = time.time()

# === INIT point 1 ===
print("[INIT] loading model Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32", flush=True)

# ... model loading code ...

# === INIT point 2 ===
print(f"[INIT] model loaded in {time.time() - START_TIME:.1f}s", flush=True)

def generate(...):
    # === REQ point 3 ===
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files=0", flush=True)

    # === GEN point 4 ===
    t_gen = time.time()
    print(f"[GEN] starting inference prompt={prompt[:40]}", flush=True)

    image = pipe(**pipe_kwargs)

    # === GEN point 5 ===
    print(f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={image.size[0]}x{image.size[1]}", flush=True)

    # ... encode to bytes ...

    # === R2 point 6 ===
    s3.put_object(...)
    url = s3.generate_presigned_url(...)
    print(f"[R2] uploaded key={key} url={url[:60]}", flush=True)

    # === OK point 7 ===
    print(f"[OK] completed in {time.time() - START_TIME:.1f}s", flush=True)
    return {"artifact": {"presigned_url": url}}
```

### Modal workers — add `START_TIME` and log points

- `@modal.enter()`: INIT 1, INIT 2
- `.generate()` / `.generate_web()`: REQ, GEN 4, GEN 5, R2, OK
- Wrap in try/except for ERR

### Flash workers — add to `__init__` and `generate()`
- `__init__`: INIT 1, INIT 2
- `.generate()`: REQ, GEN 4, GEN 5, R2, OK
- Wrap in try/except for ERR

### Beam workers — add to `load_pipeline()` / `generate()`
- `load_pipeline()`: INIT 1, INIT 2
- `.generate()`: REQ, GEN 4, GEN 5, R2, OK
- Wrap in try/except for ERR

### Vision workers (image classification)
- Replace `GEN` (inference) with `ANALYZE` tag
- Same structure, just different tag name

### H3 workers (video generation)
- `GEN` message includes video length (num_frames)
- R2 message says "video" instead of "image"

### Voice workers
- Already have granular `[WS]`, `[VAD]`, `[STT]`, `[LLM]`, `[TTS]` logs
- Add high-level `[REQ]`, `[OK]`, `[ERR]` around the full request lifecycle
- Don't touch existing granular tags

## 5. Error Handling

Wrap each `generate()`-level method in try/except:

```python
def generate(...):
    try:
        # ... existing code ...
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
```

## 6. What NOT to Change

- **NO `import logging`** — pure `print()` with `flush=True`
- **NO config files, NO log levels** — every log point is always emitted
- **NO file-based logging** — all logs go to stdout for platform log viewers
- **Worker contracts unchanged** — return types stay exactly the same
- **Worker behavior unchanged** — logs are side-effect-free prints
- **Voice worker granular logs untouched** — only add `[REQ]`/`[OK]`/`[ERR]` around them

## 7. Execution Order

1. Flux2 (3 files) — simplest, most proven
2. Krea2 (3 files) — similar to flux2
3. Vision (3 files) — simple classification, no R2
4. H3 (9 files) — more complex inputs but same pattern
5. Voice (4 files) — already partially logged, just add envelope tags