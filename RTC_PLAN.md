# RTC Plan — BE-only FastRTC Voice Chat Worker

## Goal

Realtime turns-based voice chat backend, **BE / worker-only** (no frontend whatsoever), as two platform-pure tracks:

- **Track M**: Modal CPU web worker (fastrtc; STT+TTS in-process) → Modal GPU Qwen vLLM worker
- **Track B**: Beam CPU web worker (fastrtc; STT+TTS in-process) → Beam GPU Qwen vLLM worker

No cross-platform calls. No LLM provider APIs — LLM is **hosted Qwen** per track. STT/TTS are local in-process. 3 tiers; each tier is 100% proven before the next starts.

## Base: cookbook "LLM Voice Chat", reduced to its backend core

[HF Space](https://huggingface.co/spaces/fastrtc/llm-voice-chat) / [source](https://github.com/gradio-app/fastrtc/blob/main/demo/llm_voice_chat/app.py) (97 lines). The only cookbook example whose BE core survives losing its UI: single `Stream` + `ReplyOnPause` handler. Talk to Llama 4's only structural edge (custom-frontend pattern) is out of scope.

### Transport facts (source-verified)

Fastrtc **WebRTC mode** — no WebSockets in our path:

- Signaling = one `POST /webrtc/offer` (HTTP)
- All control messages (`send_input`, `fetch_output`, `end_stream`, ...) = **WebRTC data channel**
- Media = RTP audio tracks (P2P, browser ⇄ worker container, via ICE)
- Proof: [`frontend/shared/webrtc_utils.ts`](https://github.com/gradio-app/fastrtc/blob/main/frontend/shared/webrtc_utils.ts) (zero WebSocket refs; `pc.createDataChannel("text")` + handshake) and [`backend/fastrtc/stream.py`](https://github.com/gradio-app/fastrtc/blob/main/backend/fastrtc/stream.py) `mount()` — the `/websocket/offer` route belongs to fastrtc's unused alternative WebSocket transport mode

Worker platform surface: **inbound HTTP + P2P UDP (ICE/media)**. TURN relay is the fallback when host candidates can't traverse NAT (standard server-side WebRTC; config injected into the SDP — a config swap, not an architecture change).

### Other verified fastrtc facts (`main` branch)

- `get_stt_model()` — defaults to **Moonshine ONNX, local in-process, no API** (`fastrtc[stt]`)
- `get_tts_model()` — defaults to **Kokoro, local in-process, no API** (`fastrtc[tts]`)
- Per-connection context: `get_current_context().webrtc_id`
- VAD turn-taking: `ReplyOnPause` (`fastrtc[vad]`)

## Pipeline (100% provider-free)

| Leg | Impl | Runs in |
|---|---|---|
| STT | Moonshine (`get_stt_model()`, as is) | web worker, CPU, in-process |
| LLM | **Hosted Qwen**, OpenAI-compatible `/v1/chat/completions` | GPU worker (Modal for Track M, Beam for Track B) |
| TTS | **Kokoro local** (`get_tts_model()`) | web worker, CPU, in-process |

### Kokoro reference implementation (worker-usable)

[`backend/fastrtc/text_to_speech/tts.py`](https://github.com/gradio-app/fastrtc/blob/main/backend/fastrtc/text_to_speech/tts.py) — `KokoroTTSModel`: `kokoro_onnx.Kokoro` + weights via `hf_hub_download("fastrtc/kokoro-onnx", "kokoro-v1.0.onnx" | "voices-v1.0.bin")`; CPU ONNX, 82M params; `stream_tts_sync(text)` → sentence-streamed `(sample_rate, np.float32)` chunks; options `voice/speed/lang`. Usage pattern: [`demo/talk_to_claude/app.py`](https://github.com/gradio-app/fastrtc/blob/main/demo/talk_to_claude/app.py) — `for chunk in tts_model.stream_tts_sync(text): yield chunk`.

Beam audio-worker packaging reference (fallback if TTS is ever split to its own GPU worker): [beam-cloud/examples/audio_and_transcription](https://github.com/beam-cloud/examples/tree/main/audio_and_transcription) — `zonos`, `parler-tts` (TTS), `whisper_stt`/`faster_whisper` (STT).

## The diffs (vs. the found code)

1. **LLM**: `Groq()` → `OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key="local")`; model string = the Qwen revision the track's GPU worker serves. Call shape unchanged (`chat.completions.create(messages=...)`).
2. **TTS**: ElevenLabs block → `tts_model = get_tts_model()` (Kokoro) + `stream_tts_sync` loop. Deps: drop `elevenlabs` + `ELEVENLABS_API_KEY`.
3. **History**: the example's chat history rides in the Gradio chatbot (cut). Replace with the ~5-line server-side `dict` keyed by `get_current_context().webrtc_id` (pattern from the Llama-4 example, pure backend code — without it the worker is stateless per utterance).
4. **Handler**: `response(audio)` → `stt` → chat completions (with history) → `yield` TTS chunks. Nothing else.

## Out of scope (cut, not planned)

- ❌ Gradio UI / `mount_gradio_app`, `additional_inputs=[chatbot]`, `AdditionalOutputs(chatbot)` yields (the built-in `stream.ui` is a throwaway **test client** only, never shipped)
- ❌ index.html, JS client, Gradio-UI SSE (`/outputs`), `/input_hook` — none of it (the keepalive SSE in Fleet & cost is a separate, planned endpoint)

## Fleet & cost (frugal)

- **1 container per track, no scale-out.** Modal `max_containers=1`; Beam 1-container cap (exact `@asgi` parameter confirmed in Tier 1).
- **N concurrent sessions per container** — CPU-bound (STT/TTS in-process). `Stream(concurrency_limit=N)` set explicitly (fastrtc defaults to **1**). Overflow → documented `concurrency_limit_reached` rejection, never scale-out. N validated under load in Tier 1.
- **Short idle windows**: Modal `scaledown_window=60`, Beam `keep_warm_seconds=60`.
- **Keepalive endpoint (BE contract)**: `GET /keepalive/{webrtc_id}` — SSE held open for the session's lifetime; server closes it on peer disconnect. Client opens on call start, closes on end (one-line client obligation — noted, not planned here).
  - Why: in WebRTC mode the offer POST returns instantly and media is P2P → the platform sees **zero activity during a live call**; without an in-flight request, a short window reclaims the container mid-session. With the in-flight SSE: live calls are immune to scale-down at any window; after the last call → at zero ≤60s.
- `time_limit` (max session duration) and the idle window are now independent — the `scaledown_window ≥ time_limit` workaround is deleted.
- **Cost profile**: container billed only while a call is live + up to 60s after the last disconnect. Zero in between.

## Verified platform references (official)

**Modal**

- fastrtc on Modal: [fastrtc_flip_webcam](https://modal.com/docs/examples/fastrtc_flip_webcam) — `@modal.asgi_app()`, `max_containers=1`, `@modal.concurrent(max_inputs=N)`, `scaledown_window > time_limit` (their window-outlives-sessions pattern; we deviate: short windows + keepalive endpoint — see Fleet & cost); `modal serve` = hot-reload dev loop, `modal deploy` = permanent. WebRTC-on-Modal ASGI officially proven.
- Production WebRTC: [webrtc_yolo](https://modal.com/docs/examples/webrtc_yolo) — STUN-only works on many networks; TURN escalation via free [Open Relay](https://www.metered.ca/tools/openrelay/) + `turn-credentials` Modal Secret; set `region` near users.
- Qwen on Modal: [llm_inference](https://modal.com/docs/examples/llm_inference) — vLLM + Qwen3 (Qwen3-4B-Thinking-2507-FP8), OpenAI-compatible, `@app.server`, H100.

**Beam**

- Dev loop: `beam serve app.py:handler` — live-reloads remote container, forwards logs locally ([web-server docs](https://docs.beam.cloud/v2/endpoint/web-server), [CLI ref](https://docs.beam.cloud/v2/reference/cli#serve)). Deploy: `beam deploy app.py:handler` → URL.
- Web server: `@asgi(name=..., image=Image(python_packages=[...]), concurrent_requests=N)` — handler returns the FastAPI app. Our only platform-layer need (signaling is plain HTTP).
- Networking: [pod networking](https://docs.beam.cloud/v2/pod/networking) — public URLs for exposed TCP ports; **public inbound UDP undocumented** → ICE host-candidate viability is settled empirically in Tier 1 (STUN first; TURN fallback, same config as Track M).
- No official Beam webrtc/fastrtc example exists ([beam-cloud/examples](https://github.com/beam-cloud/examples) tree: zero matches) — the Beam track is new ground, gated by Tier 1.
- Qwen on Beam: [vLLM example](https://docs.beam.cloud/v2/examples/vllm) — `VLLM(name=..., gpu="H100", vllm_args=VLLMArgs(model="Qwen/..."))` + `beam deploy app.py:llm`.

---

# Tier 1 — Scaffolding, dummy pipeline, proven locally

**Goal**: prove the RTC loop end-to-end with zero LLM, zero GPU. Two files: `web_worker_modal.py`, `web_worker_beam.py`.

- [ ] fastrtc `Stream(ReplyOnPause(handler), modality="audio", mode="send-receive")` + `stream.mount(app)`; `rtc_configuration` STUN-only
- [ ] Handler (dummy): on pause → log STT transcript (`get_stt_model()` = Moonshine, CPU) → **yield a fixed Kokoro sentence** (e.g. "RTC loop verified."). No LLM, no GPU anywhere.
- [ ] Modal wrap: `@modal.asgi_app()` + `max_containers=1` + `@modal.concurrent(max_inputs=N)` + `scaledown_window=60`. Image: `uv_pip_install("fastapi[standard]", "fastrtc[vad, stt, tts]", "openai")`
- [ ] Beam wrap: `@asgi(..., concurrent_requests=N, keep_warm_seconds=60)` + 1-container cap, `Image(python_packages=["fastapi[standard]", "fastrtc[vad, stt, tts]", "openai"])`
- [ ] Keepalive endpoint: `GET /keepalive/{webrtc_id}` — SSE tied to the session lifecycle, server closes on peer disconnect
- [ ] N validation: load N concurrent dummy sessions; per-turn latency acceptable on the container's CPU allocation
- [ ] Test client = the library's built-in `stream.ui` (test harness, not a shipped frontend)

**Local run**: `modal serve web_worker_modal.py` / `beam serve web_worker_beam.py:handler`.

**Gate (100% before Tier 2)**: on both tracks — WebRTC connects; speak → transcript logged; fixed Kokoro sentence comes back; 2 consecutive turns in one session; clean disconnect; live session survives past the 60s idle threshold (no mid-session reclaim via keepalive); container at zero ≤60s after last disconnect. First check on the Beam track = **ICE connectivity**: STUN; if host candidates fail, wire TURN (Open Relay free tier) into the RTC config — deterministic outcome either way.

## Tier 2 — Same dummy, deployed, proven

**Goal**: identical dummy pipeline on production URLs (`modal deploy` / `beam deploy`).

- [ ] Deploy both web workers, same dummy handler
- [ ] Same gate as Tier 1 against the deployed URLs
- [ ] Scale-to-zero + cold start: after last disconnect, platform status shows zero ≤60s; next connect works through cold start; wake latency acceptable
- [ ] Concurrency: `concurrency_limit` / `concurrent_requests` enforced — N+1th peer gets the documented `concurrency_limit_reached` rejection; a second peer doesn't break the first
- [ ] Real-network connectivity (STUN or TURN per Tier 1 outcome)

## Tier 3 — Business logic, deployed, flawless

**Goal**: full turns voice chat with hosted Qwen, all proven on deployed endpoints.

- [ ] **Qwen workers**: Track M = [Modal llm_inference](https://modal.com/docs/examples/llm_inference) pattern (vLLM, Qwen3 FP8, H100, `@app.server`); Track B = `VLLM(name=..., gpu="H100", vllm_args=VLLMArgs(model="Qwen/..."))` + `beam deploy`. Both expose OpenAI-compatible `/v1/chat/completions`
- [ ] Web worker handler swap per "The diffs" (LLM client → track's Qwen worker URL; Kokoro TTS; per-connection history dict)
- [ ] `LLM_BASE_URL` resolved via the contract mechanism, per track

**Gate (flawless)**: multi-turn conversation on each deployed track, history coherent across 3+ turns; STT→Qwen→TTS all local (zero provider APIs); interruption behavior per `ReplyOnPause`; per-turn latency budget logged; both tracks re-pass Tier 2's cold-start + concurrency checks with the real pipeline.

---

## Net

Tier 1 kills the platform risk (Beam ICE/UDP is the only genuinely unknown), Tier 2 kills the deployment risk, Tier 3 is pure business logic on a proven substrate. Base = LLM Voice Chat's BE core; pipeline 100% provider-free: Moonshine STT + hosted Qwen + Kokoro TTS. Fleet is frugal: 1 container per track, no scale-out, 60s idle windows kept safe by the session keepalive endpoint.
