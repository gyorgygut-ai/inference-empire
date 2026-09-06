# Phase 5 — Voice (shared extraction + pure tests; beam parked)

## 1. New `workers/voice/_shared_voice_chat.py`

Every worker type gets a shared file. Extract from
`worker_modal_cls_voice_chat.py` (702 lines) — pure helpers + constants only:

- `find_sentence_end`, `pcm_float_to_int16`, `resample_int16`, `_rid`,
  `_patch_torch_load`
- Config constants: `SAMPLE_RATE_IN`, `TTS_SR`, `MAX_NEW_TOKENS`,
  `SUPPORTED_LANGUAGES`

The worker file keeps the modal App/image/`VoiceChatPipeline`/
`RealtimeSession`/`VoiceChatWorker` shell. Full pipeline/session extraction
is a later task (noted, not in this plan). Future goal (not in plan): all
workers get implementations for all 3 providers.

## 2. Beam voice: PARKED, not tested

All 3 beam workers (`chatterbox`, `openvoice`, `qwen`) import `handlers.*` /
`realtime.*` packages plus `voices/` reference data that **do not exist in
the repo** — they are unimportable as-is. No test files for them until the
imports resolve. Decision needed (outside this plan): vendor the missing
packages or delete the workers.

## 3. Tests (mock-free by construction, one assert each)

- `workers/voice/tests/__init__.py` (empty)
- `workers/voice/tests/test_worker_modal_cls_voice_chat.py`: tests for the
  extracted pure helpers — no mocking needed (pure functions):
  parametrized `find_sentence_end` cases, `pcm_float_to_int16` round-trip,
  `_rid` uniqueness/format. Real `numpy` kept (cheap, no GPU). Setup / blank
  / act / blank / assert per case, one assert each.

## 3b. E2E tests (modal voice only; beam parked)

- `workers/voice/tests/test_e2e_worker_modal_cls_voice_chat.py` via
  `e2e_target` + `bucket`. Marked `@pytest.mark.local_e2e` /
  `@pytest.mark.deployed_e2e`.

## 4. Verify

- `pytest workers/voice -v` green. `ruff check` clean.
- `-m local_e2e workers/voice` green; then deploy test env, `-m deployed_e2e
  workers/voice` green, undeploy.
- `worker_modal_cls_voice_chat.py` imports helpers from `_shared_voice_chat`
  (no duplicated definitions left behind).

## 5. Commit

`refactor(workers): extract voice shared helpers` +
`test(workers): add voice unit tests per worker file`.
