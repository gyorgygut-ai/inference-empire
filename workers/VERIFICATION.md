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

| Worker                                            | Unit tests | E2E written | E2E run |
| ------------------------------------------------- | ---------- | ----------- | ------- |
| `worker_beam_tq_minimax_h3_nf4_fl2va.py`          | [ ]        | [ ]         | [ ]     |
| `worker_flash_cls_minimax_h3_nf4_fl2va.py`        | [ ]        | [ ]         | [ ]     |
| `worker_modal_cls_minimax_h3_nf4_fl2va.py`        | [ ]        | [ ]         | [ ]     |
| `worker_beam_tq_minimax_h3_nf4_ref2va.py`         | [ ]        | [ ]         | [ ]     |
| `worker_flash_pre_minimax_h3_nf4_ref2va.py`       | [ ]        | [ ]         | [ ]     |
| `worker_modal_cls_minimax_h3_nf4_ref2va.py`       | [ ]        | [ ]         | [ ]     |

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

- Unit: 173/173 passing (H3-NF4: 74 unit tests across 6 workers).
- E2E written: 18 e2e files (flux2, krea2, tiny_sd, vision, h3-nf4 x 3 providers; Flash e2e skipped by design).
- Known gap: all voice workers have no e2e (unit-only); Flash e2e skipped (flash dev not available).
