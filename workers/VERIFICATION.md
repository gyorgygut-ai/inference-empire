# Workers Verification

Date: 2026-09-07

Legend: `[x]` done, `[ ]` not done.

- **Unit tests**: verified locally with `pytest workers/ -k "not e2e"` → 257 passed.
- **E2E written**: test file exists in Flux pattern (invalid-reject + good-contract-and-artifact, no mocking) and collects cleanly.
- **E2E run**: passed against a real deployment. Live runs are owner-operated. `skipped` = flash e2e written but skipped (flash dev not available).

## flux2

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_beam_tq_flux2_klein9b.py` | [x] | [x] | [ ] |
| `worker_flash_cls_flux2_klein9b.py` | [x] | [x] | skipped |
| `worker_modal_cls_flux2_klein9b.py` | [x] | [x] | [ ] |

## tiny_sd

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_beam_tq_tiny_sd.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_tiny_sd.py` | [x] | [x] | skipped |
| `worker_modal_cls_tiny_sd.py` | [x] | [ ] | [ ] |

## krea2

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_beam_tq_krea2_ref2img.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_krea2_ref2img.py` | [x] | [x] | skipped |
| `worker_modal_cls_krea2_ref2img.py` | [x] | [ ] | [ ] |

## vision

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_beam_eq_small_vision.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_small_vision.py` | [x] | [x] | skipped |
| `worker_modal_cls_small_vision.py` | [x] | [ ] | [ ] |

## h3

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_beam_tq_minimax_h3_comfy.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_minimax_h3_comfy.py` | [x] | [x] | skipped |
| `worker_modal_cls_minimax_h3_comfy.py` | [x] | [ ] | [ ] |
| `worker_beam_tq_minimax_h3_fl2va.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_minimax_h3_fl2va.py` | [x] | [x] | skipped |
| `worker_modal_cls_minimax_h3_fl2va.py` | [x] | [ ] | [ ] |
| `worker_beam_tq_minimax_h3_ref2va.py` | [x] | [ ] | [ ] |
| `worker_flash_cls_minimax_h3_ref2va.py` | [x] | [x] | skipped |
| `worker_modal_cls_minimax_h3_ref2va.py` | [x] | [ ] | [ ] |
| `worker_beam_tq_minimax_h3_ref2va_comfy.py` | [x] | [ ] | [ ] |
| `worker_flash_pre_minimax_h3_ref2va_comfy.py` | [x] | [x] | skipped |
| `worker_modal_cls_minimax_h3_ref2va_comfy.py` | [x] | [ ] | [ ] |

## voice

| Worker | Unit tests | E2E written | E2E run |
|---|---|---|---|
| `worker_modal_cls_voice_chat.py` | [x] | [ ] | [ ] |
| `worker_beam_asgi_realtime_voice_chatterbox.py` | [ ] | [ ] | [ ] |
| `worker_beam_asgi_realtime_voice_qwen.py` | [ ] | [ ] | [ ] |
| `worker_beam_asgi_realtime_voice_openvoice.py` | [ ] | [ ] | [ ] |
| `worker_flash_cls_realtime_voice_chatterbox.py` | [ ] | [ ] | [ ] |
| `worker_flash_cls_realtime_voice_qwen.py` | [ ] | [ ] | [ ] |
| `worker_flash_cls_realtime_voice_openvoice.py` | [ ] | [ ] | [ ] |

## Totals

- Unit: 257/257 passing (every non-voice worker + voice chat + voice support modules; includes H3 x-rules validator and edge-case coverage).
- E2E written: 6 tests across 3 files (flux2 only; 18 non-flux files rewritten to Flux pattern pending).
- Known gap: all voice workers have no e2e (`voice_chat` unit-only; 6 realtime workers with no unit/E2E).
