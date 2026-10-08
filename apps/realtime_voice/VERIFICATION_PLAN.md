# Verification Plan — realtime-voice workers

## Phase 1 — Pre-flight (no GPU, local)

1. Run full unit suite: `npx nx run realtime-voice:test-unit` → 10/10 pass.
2. Ruff clean: `npx ruff check apps/realtime-voice` → all checks pass.
3. Validate deps: `npx nx run realtime-voice:validate-deps --skip-nx-cache` → exit 0.
4. Build artifacts: `npx nx run realtime-voice:build` → no errors, outputs in `dist/apps/realtime-voice/`.

## Phase 2 — Smoke test (local, no GPU)

1. Load dependencies via `.venv/bin/python` (avoids stale system Python 2.7 on PATH).
2. Instantiate `WhisperSTT`, `QwenLLM`, `ChatterboxTTS`, call `load()` on each.
3. Run `do_inference` with a known-good `RealtimeVoiceInput` (2400-sample base64 PCM, voice=`test-voice`).
   - Assert `audio` is non-empty base64, `transcript` matches expected text, `sample_rate` 24000.
4. Run `handle_webrtc_audio` with synthetic `np.ndarray` (2400 float32 zeros).
   - Assert returned `(24000, ndarray)` is non-empty.

## Phase 3 — Live Beam turn

1. Deploy: `npx nx run deploy-beam` (writes contract manifest, spins up worker on demand).
2. Push one task with a short real clip + `voice="test-voice"`.
3. Poll `beam logs --stub-id <worker-name>` for `[INIT]→[REQ]→[GEN]→[R2]→[OK]`.
4. Validate output: non-empty `audio`, matching `transcript`, `sample_rate` 24000.
5. Confirm no `[ERR]` after task completes; stop worker if lingering.

## Phase 4 — Live Modal turn

1. Deploy: `npx nx run deploy-modal` (app + cls, timeout 3600s).
2. Invoke one task with same payload as Beam.
3. Poll `modal app logs <app-name>` for the same tag sequence.
4. Validate output same as Beam.
5. Teardown: `modal app stop <app-name> --yes`.

## Phase 5 — Wrap-up

1. Cross-check logs from both providers — identical tag sequence, no `[ERR]`.
2. Decode audio from each turn; should be identical (same text → same audio).
3. Record commands, timestamps, and log excerpts for audit.
