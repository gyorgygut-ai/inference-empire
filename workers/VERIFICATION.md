# Workers Verification

Date: 2026-09-08

Legend: `[x]` done, `[ ]` not done.

- **Unit tests**: verified locally with `pytest workers/ -k "not e2e"` → 245 passed.
- **E2E written**: test file exists in Flux pattern (good-contract-and-artifact, no mocking) and collects cleanly.
- **E2E run**: passed against a real deployment. Live runs are owner-operated. Flash e2e written but not yet run (flash dev not available).

## vision

| Worker                             | Unit tests | E2E written | E2E run |
| ---------------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_small_vision.py`   | [x]        | [x]         | [ ]     |
| `worker_flash_cls_small_vision.py` | [x]        | [x]         | [ ]     |
| `worker_modal_cls_small_vision.py` | [x]        | [x]         | [ ]     |

## tiny_sd

| Worker                        | Unit tests | E2E written | E2E run |
| ----------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_tiny_sd.py`   | [x]        | [x]         | [ ]     |
| `worker_flash_cls_tiny_sd.py` | [x]        | [x]         | [ ]     |
| `worker_modal_cls_tiny_sd.py` | [x]        | [x]         | [ ]     |

## flux2

| Worker                              | Unit tests | E2E written | E2E run |
| ----------------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_flux2_klein9b.py`   | [x]        | [x]         | [ ]     |
| `worker_flash_cls_flux2_klein9b.py` | [x]        | [x]         | [ ]     |
| `worker_modal_cls_flux2_klein9b.py` | [x]        | [x]         | [ ]     |

## krea2

| Worker                              | Unit tests | E2E written | E2E run |
| ----------------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_krea2_ref2img.py`   | [x]        | [x]         | [ ]     |
| `worker_flash_cls_krea2_ref2img.py` | [x]        | [x]         | [ ]     |
| `worker_modal_cls_krea2_ref2img.py` | [x]        | [x]         | [ ]     |

## h3

| Worker                                        | Unit tests | E2E written | E2E run |
| --------------------------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_minimax_h3_comfy.py`          | [x]        | [x]         | [ ]     |
| `worker_flash_cls_minimax_h3_comfy.py`        | [x]        | [x]         | [ ]     |
| `worker_modal_cls_minimax_h3_comfy.py`        | [x]        | [x]         | [ ]     |
| `worker_beam_tq_minimax_h3_fl2va.py`          | [x]        | [x]         | [ ]     |
| `worker_flash_cls_minimax_h3_fl2va.py`        | [x]        | [x]         | [ ]     |
| `worker_modal_cls_minimax_h3_fl2va.py`        | [x]        | [x]         | [ ]     |
| `worker_beam_tq_minimax_h3_ref2va.py`         | [x]        | [x]         | [ ]     |
| `worker_flash_cls_minimax_h3_ref2va.py`       | [x]        | [x]         | [ ]     |
| `worker_modal_cls_minimax_h3_ref2va.py`       | [x]        | [x]         | [ ]     |
| `worker_beam_tq_minimax_h3_ref2va_comfy.py`   | [x]        | [x]         | [ ]     |
| `worker_flash_pre_minimax_h3_ref2va_comfy.py` | [x]        | [x]         | [ ]     |
| `worker_modal_cls_minimax_h3_ref2va_comfy.py` | [x]        | [x]         | [ ]     |

## voice

| Worker                                          | Unit tests | E2E written | E2E run |
| ----------------------------------------------- | ---------- | ----------- | ------- |
| `worker_modal_cls_voice_chat.py`                | [x]        | [ ]         | [ ]     |
| `worker_beam_asgi_realtime_voice_chatterbox.py` | [x]        | [ ]         | [ ]     |
| `worker_beam_asgi_realtime_voice_qwen.py`       | [x]        | [ ]         | [ ]     |
| `worker_beam_asgi_realtime_voice_openvoice.py`  | [x]        | [ ]         | [ ]     |
| `worker_flash_cls_realtime_voice_chatterbox.py` | [x]        | [ ]         | [ ]     |
| `worker_flash_cls_realtime_voice_qwen.py`       | [x]        | [ ]         | [ ]     |
| `worker_flash_cls_realtime_voice_openvoice.py`  | [x]        | [ ]         | [ ]     |

## Totals

- Unit: 245/245 passing (all 31 workers have unit files; 24 non-voice in `_shared_*` + fakes pattern, 7 voice in stub/websocket pattern; includes H3 x-rules validator and edge-case coverage).
- E2E written: all 24 non-voice workers have e2e files in the canonical flux pattern (good-contract-and-artifact, no mocking).
- Known gap: all voice workers have no e2e (unit-only; 24/24 e2e tests collected are non-voice).
