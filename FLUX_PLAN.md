# Flux2 Klein9B — Worker Fixes Plan

## Issues Found

### Modal Worker (`worker_modal_cls_flux2_klein9b.py`)

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 92 | `load(self, pipe=None)` — Modal docs: "Enter methods must take no parameters (except `self`)". `pipe` parameter violates lifecycle spec. | CRITICAL |
| 2 | 71-76 | `load_pipeline()` uses `local_files_only=True` but no model pre-download. First cold start fails. | CRITICAL |
| 3 | 83 | `gpu="L40S"` (48GB). Spec says: "GPU: smallest that fits. `L4` (24 GB) default". L40S is overkill for a 9B quantized model. | MEDIUM |
| 4 | 1-2, 99-100 | `import base64, io` at module level AND re-imported inside `_prepare_image`. Redundant. | LOW |

### Beam Worker (`worker_beam_tq_flux2_klein9b.py`)

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 5 | 186 | `secrets=[]` — Spec pattern shows `secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"]`. Secrets baked into image via `with_envs()`. Security risk. | HIGH |
| 6 | 44-51 | Missing `HF_HUB_ENABLE_HF_TRANSFER=1` in image env. Spec example includes it. | MEDIUM |
| 7 | 109-113 | `load_pipeline()` uses `local_files_only=True` but no model pre-download. `on_start=load_pipeline` fails if `hf-cache` volume is empty. | CRITICAL |
| 8 | 7 | `from pydantic import field_validator` — imported but never used. | LOW |

### Tests (Both Workers)

| # | File | Issue | Severity |
|---|------|-------|----------|
| 9 | `test_modal_cls_*.py:61` | `raw.load(pipe=FakePipeline())` — bypasses `@modal.enter()` decorator entirely. Never exercises Modal runtime lifecycle. | CRITICAL |
| 10 | `test_beam_tq_*.py:69` | `_mock_beam()` — mocks entire Beam SDK. Tests never run against real Beam runtime. | HIGH |
| 11 | All unit/e2e_local | No test covers `load_pipeline()` with `local_files_only=True`. If model not pre-cached, fails silently because `FakePipeline` bypasses it. | HIGH |

### R2 Upload + Contract

| # | File | Issue | Severity |
|---|------|-------|----------|
| 12 | `r2_upload.py` | 46-line wrapper file that must be copied to every worker folder. Spec says: inline boto3, no wrapper. | HIGH |
| 13 | `contracts/flux2_klein9b.json` | Artifact has 3 fields (`url`, `key`, `size`). Consumer only needs `presigned_url`. | MEDIUM |
| 14 | All workers | `Flux2Klein9bOutput` Pydantic model — unnecessary. Return raw dict matching contract. | MEDIUM |

---

## Fixes — Approved

### Strategy: Volume Caching (Both Platforms)

Same pattern for Modal and Beam:
1. Create persistent volume for HF cache
2. Set `HF_HOME` to volume mount path
3. Remove `local_files_only=True` — let `load_pipeline()` download on first run
4. Volume persists model weights across cold starts
5. No pre-baking, no pre-warming — first request fills volume automatically

### Modal Worker

| # | Fix | File:Line |
|---|-----|-----------|
| 1 | `@modal.enter()` signature: `load(self, pipe=None)` → `load(self)` — remove parameter entirely per Modal docs | `worker_modal_cls_flux2_klein9b.py:92` |
| 2 | Add `modal.Volume.from_name("hf-cache", create_if_missing=True)`, mount at `HF_HOME=/root/.cache/huggingface` | `worker_modal_cls_flux2_klein9b.py` (new volume + update `@app.cls` volumes param) |
| 3 | Remove `local_files_only=True` from `load_pipeline()` | `worker_modal_cls_flux2_klein9b.py:75` |
| 4 | GPU: `L40S` → `L4` per spec | `worker_modal_cls_flux2_klein9b.py:83` |
| 5 | Remove redundant module-level `import base64, io` | `worker_modal_cls_flux2_klein9b.py:1-2` |

### Beam Worker

| # | Fix | File:Line |
|---|-----|-----------|
| 6 | Migrate secrets: `secrets=[]` → `secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"]` | `worker_beam_tq_flux2_klein9b.py:186` |
| 7 | Remove `local_files_only=True` from `load_pipeline()` | `worker_beam_tq_flux2_klein9b.py:113` |
| 8 | Add `HF_HUB_ENABLE_HF_TRANSFER=1` to image env | `worker_beam_tq_flux2_klein9b.py:44-51` |
| 9 | Remove unused `field_validator` import | `worker_beam_tq_flux2_klein9b.py:7` |

### Tests

| # | Fix | File |
|---|-----|------|
| 10 | Modal lifecycle test: exercise `@modal.enter()` through Modal runtime, not `raw.load()` | `tests/test_modal_cls_flux2_klein9b_unit.py` |
| 11 | `load_pipeline()` test: verify behavior when model is missing from cache | New test in unit test files |

### R2 Upload + Contract

| # | Fix | File |
|---|-----|------|
| 12 | Delete `r2_upload.py` — inline boto3 in each worker per spec | `r2_upload.py` |
| 13 | Simplify contract: `artifact.presigned_url` only (remove `key`, `size`) | `contracts/flux2_klein9b.json` |
| 14 | Delete `Flux2Klein9bOutput` models from all workers — return raw dict | All worker files |
| 15 | Inline boto3 R2 upload in each worker's `generate()` method | All worker files |
| 16 | Add `boto3` to each worker's `pip_install` | All worker files |

### R2 Migration — Remaining Workers (krea2, h3, flux2 flash)

All workers below still import deleted `r2_upload.py` or use inline `Artifact(url, key, size)` model. Each needs: remove `r2_upload` import, delete Output model, inline boto3, return `{"artifact": {"presigned_url": ...}}`.

#### krea2 workers

| # | Fix | File |
|---|-----|------|
| 19 | Inline boto3, delete `Krea2Ref2ImgOutput`, delete `krea2/r2_upload.py` | `krea2/worker_beam_tq_krea2_ref2img.py` |
| 20 | Inline boto3, delete `Krea2Ref2ImgOutput` | `krea2/worker_modal_cls_krea2_ref2img.py` |
| 21 | Inline boto3, delete `Output` model | `krea2/worker_flash_cls_krea2_ref2img.py` |

#### h3 beam workers

| # | Fix | File |
|---|-----|------|
| 22 | Inline boto3, delete `MiniMaxH3Ref2VAOutput` | `h3/worker_beam_tq_minimax_h3_ref2va.py` |
| 23 | Inline boto3, delete `MiniMaxH3Fl2VAOutput` | `h3/worker_beam_tq_minimax_h3_fl2va.py` |
| 24 | Inline boto3, delete `Output` model | `h3/worker_beam_tq_minimax_h3_ref2va_comfy.py` |

#### h3 flash workers

| # | Fix | File |
|---|-----|------|
| 25 | Inline boto3, delete `Output` model | `h3/worker_flash_cls_minimax_h3_ref2va.py` |
| 26 | Inline boto3, delete `Output` model | `h3/worker_flash_cls_minimax_h3_fl2va.py` |
| 27 | Inline boto3, delete `Output` model | `h3/worker_flash_cls_minimax_h3_comfy.py` |
| 28 | Inline boto3, delete `Output` model | `h3/worker_flash_pre_minimax_h3_ref2va_comfy.py` |

#### h3 modal workers

| # | Fix | File |
|---|-----|------|
| 29 | Inline boto3, delete `MiniMaxH3Ref2VAOutput` | `h3/worker_modal_cls_minimax_h3_ref2va.py` |
| 30 | Inline boto3, delete `MiniMaxH3Fl2VAOutput` | `h3/worker_modal_cls_minimax_h3_fl2va.py` |

#### flux2 flash worker

| # | Fix | File |
|---|-----|------|
| 31 | Inline boto3, delete `Output` model (already broken — r2_upload deleted) | `flux2/worker_flash_cls_flux2_klein9b.py` |

#### Cleanup

| # | Fix | File |
|---|-----|------|
| 32 | Delete `krea2/r2_upload.py` (separate copy, no longer needed) | `krea2/r2_upload.py` |

---

## Verification

| # | Task |
|---|------|
| 17 | Deploy Modal flux2 → generate image → verify contract + R2 artifact |
| 18 | Deploy Beam flux2 → generate image → verify contract + R2 artifact |

---

## Execution Order

1. Update contract JSON (item 13) — DONE
2. Fix Modal flux2 worker (items 1-5, 12, 14-16) — DONE
3. Fix Beam flux2 worker (items 6-9, 12, 14-16) — DONE
4. Fix flux2 tests (items 10-11) — DONE
5. Migrate flux2 flash worker (item 31)
6. Migrate krea2 workers (items 19-21)
7. Migrate h3 beam workers (items 22-24)
8. Migrate h3 flash workers (items 25-28)
9. Migrate h3 modal workers (items 29-30)
10. Delete krea2/r2_upload.py (item 32)
11. Deploy + verify Modal flux2 (item 17)
12. Deploy + verify Beam flux2 (item 18)
