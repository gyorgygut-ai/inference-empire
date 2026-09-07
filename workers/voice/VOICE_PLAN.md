# Voice Workers — ty Fix Plan

Date: 2026-09-07
Source: `uv run ty check` → 269 diagnostics, all in `workers/voice/`

## Fixes

### 1. Unresolved imports (external runtime-only deps)
These packages are imported inside functions at runtime but not in the project lockfile.

| File | Line | Fix |
|---|---|---|
| `handlers/voice_converter.py` | 59-60 | `# ty: ignore[unresolved-import]` |
| `realtime/vad.py` | 36 | `# ty: ignore[unresolved-import]` |
| `worker_modal_cls_voice_chat.py` | 53, 160 | `# ty: ignore[unresolved-import]` |

### 2. `self._loop` narrowing — `AbstractEventLoop | None`
`# type: ignore[union-attr]` is mypy syntax — ty ignores it. Replace with `# ty: ignore` or use local `loop = self._loop` after the guard.

| File | Lines |
|---|---|
| `realtime/session.py` | 143, 189, 228, 232, 249, 254, 256, 258, 260 |
| `worker_beam_asgi_realtime_voice_openvoice.py` | 146, 172 |

### 3. `model.generate(**gen_kwargs)` — streamer type mismatch
`TextIteratorStreamer` not assignable to `BaseStreamer | None` in ty's view of transformers.

| File | Line | Fix |
|---|---|---|
| `handlers/llm.py` | 78 | `# ty: ignore[invalid-argument-type]` |
| `worker_modal_cls_voice_chat.py` | 492 | `# ty: ignore[invalid-argument-type]` |

### 4. Test fake assignments
| File | Line | Fix |
|---|---|---|
| `tests/test_handlers_wrappers.py` | 70 | `# ty: ignore[invalid-assignment]` |
| `tests/test_handlers_wrappers.py` | 118 | `# ty: ignore[invalid-assignment]` |

### 5. Beam API misuse
| File | Line | Issue | Fix |
|---|---|---|---|
| `worker_beam_asgi_realtime_voice_openvoice.py` | 199 | `gpu=None` not `GpuType` | Cast or ignore |
| `worker_beam_asgi_realtime_voice_openvoice.py` | 49 | `.with_envs(str, str)` ambiguous | Pass dict |

### 6. Real import bug (flash voice workers)
`worker_flash_cls_realtime_voice_{chatterbox,qwen,openvoice}.py` import `RealtimeVoiceInput, do_inference, load_dependencies` from `_shared_voice_chat` but that file only exports `VoiceChatInput`.

Fix: add missing exports to `_shared_voice_chat.py` or correct the imports.
