# Realtime Voice Chat Worker

**Value Proposition**: A production-deployable realtime voice chat worker on Modal and Beam, built on Hugging Face `speech-to-speech` (WebRTC transport, OpenAI Realtime protocol), running four fixed models and reference-voice cloning, consumed by the existing frontend through TanStack AI's realtime interfaces.

**Goal**: `npx nx run workers-voice:deploy-modal` and `npx nx run workers-voice:deploy-beam` each produce a serverless WebRTC endpoint where a browser can speak, hear a reply, and use a cloned reference voice — with every acceptance criterion proven by executed evidence.

---

## Verified Baseline

Every decision below is grounded in inspected source. No assumptions remain.

| Fact | Source |
|---|---|
| `Qwen/Qwen3.5-4B`, `nvidia/parakeet-tdt-0.6b-v3`, `Qwen/Qwen3-TTS-12Hz-1.7B-Base` all exist on the Hub | `GET huggingface.co/api/models/{id}` → `200` |
| Upstream default pipeline **is** the mandated stack: Silero VAD v5 → Parakeet TDT → Qwen3.5-4B → Qwen3-TTS | `README.md` "How it works", "Supported Components" |
| Upstream serves the OpenAI Realtime protocol over **WebSocket and WebRTC** | `README.md` "Realtime API" |
| Pin target | tag `v1.1.0` = commit `8ebde045cb7d72f5acd55327b80cfa1670a33936` |
| WebRTC extra is `aiortc` | `pyproject.toml` `[project.optional-dependencies] webrtc` |
| ICE servers come from env `SPEECH_TO_SPEECH_ICE_SERVERS` | `webrtc_session.py:51` |
| SDP signalling routes: `POST /v1/realtime/calls`, WS `/v1/realtime` | `websocket_router.py:676`, `:553` |
| ASGI factory seam: `create_app(pool, stop_event, llm_proxy_config=None)` | `websocket_router.py` |
| Pool construction: `_build_pipeline_unit(index, stop_event, module_kwargs, vad_handler_kwargs, stt_backend, llm_backend, tts_backend)` | `s2s_pipeline.py:586` |
| Qwen3-TTS voice cloning flags: `--qwen3_tts_model_name …-Base --qwen3_tts_ref_audio --qwen3_tts_ref_text` | `TTS/README.md` §6 |
| `qwentts-cpp-python` wheel is `manylinux_2_39` (glibc ≥ 2.39, e.g. Ubuntu 24.04) | `README.md` "CUDA Note for Qwen3-TTS" |
| Modal web functions: HTTP + WebSocket, **no inbound UDP**; Sandboxes expose TCP only | `modal.com/docs/guide/webhooks`, `/guide/sandbox-networking` |
| Beam exposed ports: SSL-terminated TCP/WS only, **no inbound UDP** | `docs.beam.cloud/v2/sandbox/networking`, `/v2/pod/networking` |
| `@asgi` / `@realtime` request timeout: default 180 s, gateway cap 600 s | `docs.beam.cloud/v2/topics/timeouts-and-retries` |
| aiortc parses `turn:`/`turns:` URIs, `?transport=udp\|tcp`; aioice implements the TURN client and relay candidates | `aiortc/rtcicetransport.py:106-135`, `aioice/turn.py`, `aioice/ice.py:95` |
| TURN credentials without a Cloudflare account: HF-token proxy | `fastrtc/credentials.py` `CLOUDFLARE_FASTRTC_TURN_URL = "https://fastrtc-turn-service.hf.space/credentials"` |
| Existing `realtime_voice` worker is a different project: faster-whisper + Qwen2.5-3B + Chatterbox; Modal exposes `@modal.fastapi_endpoint(POST)` only; Beam is `@task_queue`; `volumes=[]` | `apps/workers/realtime_voice/**` |
| TanStack `RealtimeAdapter`/`RealtimeConnection` are client interfaces with no self-hosted implementation; `@tanstack/ai-openai@1.0.0` hardcodes `https://api.openai.com/v1/realtime` | `@tanstack/ai/dist/esm/realtime/types.d.ts`, `@tanstack/ai-openai/src/realtime/adapter.ts:18` |

---

## Global Engineering Rules

**No Guessing**

- Inspect actual repository files, installed package types, upstream source, configuration, and deployment documentation before making decisions.
- Verify APIs, model compatibility, event payloads, runtime requirements, cache paths, and deployment commands against authoritative sources.
- Never invent APIs, configuration options, model capabilities, or expected behavior.
- Record the source reference or executable test supporting each important decision.

**No Hand-Rolling**

- Reuse Hugging Face `speech-to-speech` for its inference pipeline, realtime protocol, streaming, WebRTC transport, and session lifecycle.
- Reuse TanStack AI's existing realtime interfaces; implement only the adapter that has no upstream implementation.
- Follow the existing Beam and Modal worker patterns in `apps/workers/`.
- Add custom glue only for a verified incompatibility or a missing requirement.
- Do not introduce speculative abstractions, generic frameworks, duplicate pipelines, or unnecessary dependencies.

**Minimal, Elegant Code**

- Implement the smallest complete solution.
- Follow existing repository conventions; reuse dependencies, scripts, shared code, and deployment configuration.
- Every new file and abstraction must have a demonstrated purpose.
- Do not refactor unrelated code.
- Never weaken lint rules, type checks, tests, or acceptance criteria to make the implementation pass.

**Prove Every Phase**

- Implement and verify one phase at a time.
- Run actual commands and tests; do not infer success from code inspection.
- Mark criteria **PASS**, **FAIL**, or **BLOCKED**. A blocked or untested criterion is never a pass.
- After changing a verified component, rerun the affected checks.
- Do not proceed past a failed mandatory acceptance criterion.

---

## Architecture

### Project: new worker family `voice`

`apps/workers/realtime_voice/` is a separate, existing project (faster-whisper / Qwen2.5 / Chatterbox, task-queue shaped). It is not modified. The new family follows the repo's `apps/workers/{family}` convention end to end.

```
apps/workers/voice/
  project.json                          workers-voice; build modal|beam; deploy-modal|deploy-beam
  pyproject.toml                        speech-to-speech[webrtc]==1.1.0
  uv.lock
  beam.yaml
  .beamignore
  .gitignore
  __init__.py
  shared/
    worker_voice.py                     model args, ASGI app factory, TURN, session cap
    contract_voice.json                 session contract
  worker_modal_cls_voice.py             @modal.asgi_app() entry point
  worker_beam_asgi_voice.py             @asgi entry point
  tests/
    test_worker_voice.py                unit: args, TURN parsing, validation
    test_e2e_voice.py                   e2e: live WebRTC turn against a deployment
packages/schemas/voice/schema.json      generated from contract
apps/workers/AGENTS.md                  family list updated
```

### Model stack (exact, non-substitutable)

| Component | Model | Configured by |
|---|---|---|
| VAD | Silero VAD v5 | upstream default, no flag |
| STT | `nvidia/parakeet-tdt-0.6b-v3` | `--stt parakeet-tdt` (default backend) |
| LLM | `Qwen/Qwen3.5-4B` | `--model_name Qwen/Qwen3.5-4B` |
| TTS + cloning | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | `--tts qwen3 --qwen3_tts_model_name Qwen/Qwen3-TTS-12Hz-1.7B-Base --qwen3_tts_ref_audio <wav> --qwen3_tts_ref_text <transcript>` |

Single source of truth for these values is `shared/worker_voice.py`; both provider entry points import it. No model ID is repeated in a provider file.

### Transport: WebRTC over TURN

- Worker side: aiortc gathers a `relay` candidate from `SPEECH_TO_SPEECH_ICE_SERVERS` and dials outbound. No inbound port is required.
- Browser side: same `iceServers` handed to `RTCPeerConnection`; browser dials outbound.
- Signalling: `POST /v1/realtime/calls` over HTTPS — served natively by Modal and Beam.
- TURN credentials: `GET /turn-credentials` on the worker mints short-lived credentials from the HF-token proxy (`fastrtc-turn-service.hf.space/credentials`, `HF_TOKEN` already present in every provider secret set) and returns them as `{"iceServers": [...]}`. The same call refreshes `SPEECH_TO_SPEECH_ICE_SERVERS` in the worker process, so the browser and aiortc always share one valid credential.
- Credential TTL 900 s, session cap 600 s.

### Hosting: one seam, two providers

Both providers return the same ASGI app built by `shared/worker_voice.build_app()`:

```python
pool = [build_unit(i) for i in range(num_pipelines)]   # upstream _build_pipeline_unit
app = create_app(pool=pool, stop_event=stop_event)     # upstream factory
```

- Modal: `@modal.asgi_app()` on a class method, models + app built in `@modal.enter()`.
- Beam: `@asgi(on_start=load, volumes=[beam_volume(CACHE_PATH)], ...)` returning the same app.
- No subprocess, no reverse proxy, no port forwarding, no provider-specific transport code.

### Lifecycle and scale-to-zero

| Concern | Decision |
|---|---|
| Concurrency | `max_containers=1` (Modal) / `workers`+`concurrent_requests` (Beam) — signalling and media always land on the same container |
| Idle scale-down | Modal `scaledown_window=900`; Beam `keep_warm_seconds` set to the same value |
| Mid-call keepalive | Client sends `GET /health` every 30 s, resetting the idle timer |
| Session ceiling | 600 s, enforced by the Beam gateway cap; the client surfaces it as a visible limit |
| Model load | once per container in `@modal.enter()` / Beam `on_start`; never per request |

### Cache

| Provider | Mechanism |
|---|---|
| Modal | `volumes={MODAL_HF_MOUNT: hf_cache_vol}` via `modal_volume()`, `HF_HOME=MODAL_HF_MOUNT` via `modal_env()` |
| Beam | `volumes=[beam_volume(BEAM_CACHE_PATH)]`, `HF_HOME=BEAM_CACHE_PATH` via `beam_env()` |
| TTS reference cache | `--qwen3_tts_ref_cache_dir` pointed inside the mounted cache |

No custom download manager. Upstream populates the HF cache on first use.

### Images

Both providers build on **Ubuntu 24.04 + CUDA 12.8 + Python 3.11**, the only combination that satisfies `qwentts-cpp-python`'s `manylinux_2_39` wheel and upstream's `requires-python >= 3.11`.

- Modal: `modal.Image.from_registry("nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04", add_python="3.11")`
- Beam: `Image(base_image="nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04", python_version="python3.11")`
- Dependencies: `speech-to-speech[webrtc]==1.1.0`, single list in `shared/worker_voice.py`

### Contract

`worker-service/voice-deploy` declares `WORKER_RESOLVED_MODAL_URL` / `WORKER_RESOLVED_BEAM_URL` as `fulfills`. Upstream exposes no request/response turn endpoint, so the schema describes a session service, not an audio→transcript call:

```json
{"title": "VoiceService", "type": "object", "required": ["url", "health"],
 "properties": {"url": {"type": "string"}, "health": {"type": "string"}}}
```

---

## Phase 0: Prove WebRTC over TURN on Serverless

**Goal**: Prove the load-bearing transport assumption before any product work. Everything downstream is worthless if this fails.

**Implementation**

- Build a throwaway Modal app: `@modal.asgi_app()`, aiortc echo track, `SPEECH_TO_SPEECH_ICE_SERVERS` from the HF-token TURN proxy, `POST /calls` SDP exchange.
- Connect from a browser on a different network with the same `iceServers`.
- Delete the throwaway app after evidence is captured; nothing from it lands in `apps/workers/voice/`.

**Acceptance and verification**

- [ ] `GET fastrtc-turn-service.hf.space/credentials` returns `iceServers` using the repo's `HF_TOKEN`.
- [ ] The deployed app answers the SDP offer with a `relay` candidate in the answer.
- [ ] Browser `iceConnectionState` reaches `connected` with a relay candidate pair selected.
- [ ] Audio echoed by the worker is audible in the browser for at least 30 s.
- [ ] The container stays alive for a 3-minute call while the client sends the 30 s heartbeat.
- [ ] All evidence captured: SDP excerpt, ICE candidate types, browser state log, Modal container logs.

**Gate**: No Phase 1 work until relay-relayed media is proven end to end.

---

## Phase 1: Pin Upstream and Verify Compatibility

**Goal**: Establish the exact implementation strategy and a reproducible environment.

**Implementation**

- Pin `speech-to-speech[webrtc]==1.1.0` and commit `8ebde045cb7d72f5acd55327b80cfa1670a33936`; commit `uv.lock`.
- Verify the four model IDs resolve through the actual loading paths used by the pinned revision.
- Verify the TTS Base model's reference-conditioning path through `--qwen3_tts_ref_audio` / `--qwen3_tts_ref_text`.
- Confirm the exact startup sequence for `create_app` + pool + handler threads at the pinned commit, and record it in `shared/worker_voice.py` as the single seam.
- Start the upstream baseline with its documented command in the target image and capture logs.
- Inspect `apps/workers/{flux2,h3_fl2va}` for the Modal/Beam conventions being reused; record exact file references.

**Acceptance and verification**

- [ ] `uv.lock` pins the exact upstream version and commit; a clean `uv sync` succeeds in the target image.
- [ ] All four model IDs are present in the worker's configuration constants.
- [ ] Reference-conditioning flags exist and are accepted by the pinned revision.
- [ ] The exact pool/app/handler startup sequence is recorded with source line references.
- [ ] `speech-to-speech serve` starts in the Ubuntu 24.04 image with the mandated models and logs `Ready`.
- [ ] Existing Beam/Modal cache conventions are documented with file references.

**Evidence**: lockfile, resolved versions, startup log, source line references.

**Gate**: Do not proceed until dependencies install, the baseline starts, and the hosting seam is recorded.

---

## Phase 2: Implement the Shared Voice Worker

**Goal**: The smallest reusable core under `apps/workers/voice/shared/worker_voice.py`.

**Implementation**

- `VOICE_ARGS`: the exact CLI argument list for the four models, reference voice, language, and pipeline size.
- `build_app()`: pool → `create_app`, returning the ASGI app; starts and stops handler threads with the app lifecycle.
- `turn_ice_servers()`: mints credentials from the HF-token proxy; used by `/turn-credentials` and by the worker's own ICE env.
- `GET /health` and `GET /turn-credentials` routes.
- Startup validation: missing `HF_TOKEN`, missing reference audio/transcript, or unreadable reference files fail with actionable errors.
- Session isolation comes from upstream's per-session `PipelineUnit` claim; no custom session state is added.

**Acceptance and verification**

- [ ] All four model IDs appear only in `shared/worker_voice.py`.
- [ ] No provider-specific import exists in the shared module.
- [ ] `uv run --locked --group test ruff check .` exits `0`.
- [ ] `uv run --locked --group test ty check .` exits `0`.
- [ ] `uv run --locked --group test pytest apps/workers/voice` passes.
- [ ] New unit tests cover: arg construction, TURN response parsing, missing-config failure paths.
- [ ] The worker starts locally and serves `/health` `200`.
- [ ] Invalid configuration fails clearly (missing reference transcript, missing `HF_TOKEN`).
- [ ] Two concurrent sessions receive independent transcripts and audio; no cross-talk.
- [ ] No unhandled exceptions in the smoke run.

**Evidence**: command output with exit codes, test report, startup and session logs.

**Gate**: Do not proceed until statically clean, locally started, and session-isolated.

---

## Phase 3: Deploy the Modal Worker

**Implementation**

- `worker_modal_cls_voice.py`: `modal.App`, image per Architecture, `@modal.enter()` building app and models, `@modal.asgi_app()` returning it.
- `max_containers=1`, `scaledown_window=900`, `gpu="L4"`, `memory=32768`, HF volume mount, dotenv secret.
- `project.json` `build:modal` + `deploy-modal` with `fulfills: WORKER_RESOLVED_MODAL_URL`.
- `packages/schemas/voice/schema.json` generated from `contract_voice.json`.

**Acceptance and verification**

- [ ] Entry point follows existing Modal worker conventions (image, volume, secret, enter, timeout).
- [ ] `npx nx run workers-voice:build:modal` exits `0`.
- [ ] `npx nx run workers-voice:deploy-modal` exits `0` and writes `WORKER_RESOLVED_MODAL_URL`.
- [ ] Cold start downloads models into the mounted volume; warm start reuses them (log evidence of both).
- [ ] All four model IDs appear in initialization logs.
- [ ] `GET /health` returns `200` on the deployed URL.
- [ ] `GET /turn-credentials` returns valid `iceServers` from the deployed URL.
- [ ] A WebRTC session from a browser on another network connects, relays, and disconnects cleanly.
- [ ] No model substitution or fallback appears in logs.

**Evidence**: build/deploy output, cold and warm cache logs, deployed URL, health and TURN responses, session log.

**Gate**: Do not proceed until the Modal deployment serves a live WebRTC session.

---

## Phase 4: Deploy the Beam Worker

**Implementation**

- `worker_beam_asgi_voice.py`: `@asgi` with the shared app, `on_start` model load, `volumes=[beam_volume(BEAM_CACHE_PATH)]`, `beam_env()`, `keep_warm_seconds` matching the Modal idle window, `concurrent_requests` sized to the pipeline pool.
- `project.json` `build:beam` + `deploy-beam` with `fulfills: WORKER_RESOLVED_BEAM_URL`.
- `beam.yaml` for the family.

**Acceptance and verification**

- [ ] Entry point follows existing Beam worker conventions (image, cache volume, `on_start`, checkpoint/keep-warm settings).
- [ ] `npx nx run workers-voice:build:beam` exits `0`.
- [ ] `npx nx run workers-voice:deploy-beam` exits `0` and writes `WORKER_RESOLVED_BEAM_URL`.
- [ ] Cold start downloads models into the Beam cache volume; warm start reuses them (log evidence of both).
- [ ] All four model IDs appear in initialization logs.
- [ ] `GET /health` and `GET /turn-credentials` return `200` on the deployed URL.
- [ ] A WebRTC session from a browser on another network connects, relays, and disconnects cleanly.
- [ ] The 600 s session ceiling is observed and surfaced, not silent.

**Evidence**: build/deploy output, cold and warm cache logs, deployed URL, health and TURN responses, session log.

**Gate**: Do not proceed until the Beam deployment serves a live WebRTC session.

---

## Phase 5: TanStack AI Realtime Adapter

**Goal**: Connect the real frontend through TanStack AI's interfaces with the smallest possible custom surface. This precedes voice proof because it is the only WebRTC client in the system.

**Implementation**

- Implement `RealtimeAdapter` + `RealtimeConnection` for the self-hosted server, per the installed interfaces in `@tanstack/ai/dist/esm/realtime/types.d.ts`.
- `connect(token)`: fetch `iceServers` from `/turn-credentials`, create `RTCPeerConnection`, capture mic via one `MediaStreamAudioSourceNode`, POST the SDP offer to `/v1/realtime/calls`, apply the answer, play the remote track.
- Map server events to TanStack events: `speech_started`/`speech_stopped` → `mode_change`; transcription → `transcript`; `response.output_audio_transcript.*` → `transcript`; `response.done` → `message_complete`; `response.cancel` → `interrupted`; `error` → `error`.
- `interrupt()` → `response.cancel`; `sendText()` → `conversation.item.create` + `response.create`; heartbeat `GET /health` every 30 s while connected.
- `getToken` returns a static token; the adapter is the only consumer.
- Frontend config selects the Modal or Beam URL by environment variable — one implementation, two targets.

**Acceptance and verification**

- [ ] Frontend lint, type check, and production build all exit `0`.
- [ ] The adapter satisfies the installed `RealtimeAdapter`/`RealtimeConnection` types with no `any` or unsafe casts.
- [ ] Mic capture starts and stops; the browser releases the device on disconnect.
- [ ] Incoming transcripts and responses update the UI.
- [ ] Playback follows `response.output_audio.delta` ordering.
- [ ] Connection failure and session termination are visible in the UI.
- [ ] The same build connects to the Modal URL and to the Beam URL by configuration alone.
- [ ] Adapter unit tests cover event mapping and the failure path.

**Evidence**: lint/type/build output, adapter tests, recorded event traces.

**Gate**: Do not proceed until the frontend drives a connection to both deployments.

---

## Phase 6: Prove Inbound Voice

**Goal**: Actual audio through WebRTC, transcribed by the mandated VAD and STT models.

**Implementation**

- Reuse upstream VAD, STT, turn tracking, and transcription events. No custom audio path.

**Acceptance and verification**

- [ ] WebRTC connects and ICE selects a relay candidate pair.
- [ ] The microphone track is negotiated and audio frames reach the worker.
- [ ] Silero VAD v5 is confirmed active; `speech_started` / `speech_stopped` fire on real speech.
- [ ] `nvidia/parakeet-tdt-0.6b-v3` is confirmed active.
- [ ] A known utterance produces a nonempty transcript matching the audio and session.
- [ ] Silence produces no fabricated utterances.
- [ ] Invalid audio and processing failures surface observable errors.
- [ ] Disconnect releases the session; a new client claims the unit cleanly.
- [ ] The test passes repeatedly on both Modal and Beam.

**Evidence**: ICE logs, candidate types, active model identifiers, captured transcripts, repeated runs.

**Gate**: Do not proceed until inbound voice is proven on both providers.

---

## Phase 7: Prove LLM Response and Speech Generation

**Implementation**

- Reuse upstream LLM streaming, TTS streaming, and cancellation.

**Acceptance and verification**

- [ ] `Qwen/Qwen3.5-4B` is confirmed active and produces a nonempty response.
- [ ] `Qwen/Qwen3-TTS-12Hz-1.7B-Base` is confirmed active and produces decodable audio.
- [ ] Audio reaches the browser over the WebRTC media track and is audible.
- [ ] Transcript, response text, audio, and session belong to the same turn.
- [ ] Repeated request/response cycles succeed.
- [ ] Model errors and timeouts are observable.
- [ ] The test passes on both providers with unchanged model IDs.

**Evidence**: transcript, response text, active model identifiers, decoded audio sample, browser playback confirmation.

**Gate**: Do not proceed until both deployments receive voice and return speech.

---

## Phase 8: Prove Reference-Voice Cloning

**Implementation**

- `--qwen3_tts_model_name Qwen/Qwen3-TTS-12Hz-1.7B-Base` with `--qwen3_tts_ref_audio` and `--qwen3_tts_ref_text`.
- Reference assets stored beside the worker and mounted; validation at startup and per session.

**Acceptance and verification**

- [ ] The Base model loads in both deployed runtimes.
- [ ] Reference audio and transcript pass validation; missing or mismatched inputs fail clearly.
- [ ] Reference-conditioned synthesis completes; output is nonempty, decodable, and playable.
- [ ] Logs confirm reference conditioning was applied, not default-voice synthesis.
- [ ] A second valid reference works through the same interface.
- [ ] Cloning works through the frontend conversation flow.
- [ ] The test passes on both providers.

**Evidence**: conditioning inputs, inference logs, validation results, playable samples.

**Gate**: Do not proceed until reference-conditioned synthesis is proven on both deployments.

---

## Phase 9: Prove Realtime Conversation Behaviour

**Implementation**

- Reuse upstream streaming, barge-in, cancellation, and buffer management. Add custom handling only for a demonstrated protocol gap.

**Acceptance and verification**

- [ ] Two consecutive turns succeed in one session with preserved context.
- [ ] Streaming events arrive in valid order.
- [ ] Interrupting a response cancels generation and stops playback.
- [ ] Cancelled audio never plays after the next response starts.
- [ ] Sessions and buffers are isolated between clients.
- [ ] Disconnect and reconnect leave no stale session.
- [ ] Repeated turns show no unbounded resource growth.
- [ ] No protocol errors or unhandled exceptions across the defined run.
- [ ] Behaviour is identical on both providers.

**Evidence**: multi-turn trace, cancellation and reconnect results, resource observations.

**Gate**: Do not proceed until realtime behaviour is verified on both providers.

---

## Phase 10: Final Deployment and Verification

**Acceptance and verification**

- [ ] Both entry points follow repository conventions; shared logic is reused, not duplicated.
- [ ] Both deployments use the four exact model IDs.
- [ ] Both use the established cache and lifecycle strategies.
- [ ] Both build, deploy, and reach a verified ready state.
- [ ] `GET /health` and `GET /turn-credentials` respond correctly on both.
- [ ] Inbound voice, LLM response, TTS audio, cloning, multi-turn, interruption, disconnect, and reconnect all pass on both.
- [ ] Lint, type check, tests, and production build pass.
- [ ] No unexpected runtime errors during the verification run.
- [ ] No unused abstractions, duplicated pipelines, or unrelated refactors remain.
- [ ] Every criterion is marked **PASS**, **FAIL**, or **BLOCKED** with evidence.

**Final deliverables**

- Source under `apps/workers/voice/`.
- Modal and Beam entry points and deployment configuration.
- Pinned upstream revision and lockfile.
- Exact configuration for the four models.
- Commands: install, lint, type check, test, run locally, deploy, verify.
- Test results and runtime logs.
- Deployment identifiers and URLs for both providers.
- Health and TURN results for both deployments.
- Evidence of inbound voice, generated speech, cloning, and multi-turn interaction on both.
- Acceptance matrix linking every criterion to its evidence.

---

## Commands

| Purpose | Command |
|---|---|
| Install | `uv sync --locked` |
| Lint | `uv run --locked --group test ruff check .` |
| Type check | `uv run --locked --group test ty check .` |
| Dead code | `uv run --locked --group test vulture .` |
| Unit tests | `uv run --locked --group test pytest apps/workers/voice` |
| Local run | `uv run speech-to-speech serve --host 0.0.0.0 --port 8765 <VOICE_ARGS>` |
| Build Modal | `npx nx run workers-voice:build:modal` |
| Deploy Modal | `npx nx run workers-voice:deploy-modal` |
| Build Beam | `npx nx run workers-voice:build:beam` |
| Deploy Beam | `npx nx run workers-voice:deploy-beam` |
| Verify all | `npx nx run-many -t verify --nxBail --parallel=1` |

---

## Required Agent Workflow

For every phase:

1. Inspect the existing implementation, types, documentation, and configuration.
2. Identify the smallest implementation that satisfies the phase.
3. Reuse existing code and conventions wherever possible.
4. Implement only the current phase.
5. Run its actual lint, type-check, test, runtime, or deployment checks.
6. Fix failures and rerun affected checks.
7. Record commands, exit codes, observed results, and evidence.
8. Mark every criterion **PASS**, **FAIL**, or **BLOCKED**.
9. Proceed only when all mandatory criteria pass.

**Never guess. Never silently substitute a model. Never recreate existing worker infrastructure. Never hand-roll functionality already available upstream. Never claim success without executed proof.**
