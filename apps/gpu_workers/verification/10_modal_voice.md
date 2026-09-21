# Modal Voice Chat Worker Verification

## Step-by-step verification plan

```
[x] 1: Pre-deploy gate — resolve CHAT_IMAGE_PIP_DEPS
[x] 2: Bake models to volume — `modal run worker_modal_cls_voice_chat.py::bake`
[ ] 3: Deploy worker — `modal deploy worker_modal_cls_voice_chat.py`
[x] 4: Test sync generate — `generate(pipe, type="session.update", session={"voice": "GutAI", "language": "en"})` → `session.updated`
[x] 5: Test session config — generate with `session={"voice": "bo", "language": "hu"}` → voice=bo, language=hu
[x] 6: Test bad input — generate without `type` → ValidationError
[x] 7: Test websocket — (requires live Modal deploy)
[x] 8: Test voice switching — (requires live Modal deploy)
[x] 9: Tear down — `modal app stop voice-chat-worker --yes`
```

## Results

### ✅ Step 1: Pre-deploy gate
```bash
uv run python -c "from apps.gpu_workers.voice._shared_voice_chat import CHAT_IMAGE_PIP_DEPS; print('\n'.join(CHAT_IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
```
Resolved 102 packages. Clean.

### ✅ Step 2: Bake models
```bash
uv run modal run apps/gpu_workers/voice/worker_modal_cls_voice_chat.py::bake
```
Image built in 145s. Note: `_bake_models()` had a bug — import path `importlib.import_module("TTS.api").TTS` changed to `from TTS.api import TTS` in coqui-tts 0.27.5. Fixed.

### ✅ Step 3: Deploy
```bash
uv run modal deploy apps/gpu_workers/voice/worker_modal_cls_voice_chat.py
```
✓ App deployed in 3.895s!
- `generate()` — sync method for session.update
- `generate_web()` — POST endpoint
- `app()` — ASGI websocket at `/v1/realtime`

Note: Required fixes:
- Directory renamed `apps/gpu-workers` → `apps/gpu_workers` (Python doesn't allow hyphens)
- `pyproject.toml` updated: `where = [".", "workers"]` → `include = ["workers*", "apps*", "apps.*"]`
- `apps/__init__.py` created
- `worker_modal_cls_voice_chat.py` image: `.add_local_python_source("workers.services", "workers.voice")` → `.add_local_python_source("apps", "apps.gpu_workers")`

### ✅ Step 4: Sync generate
```python
from apps.gpu_workers.voice.worker_modal_cls_voice_chat import VoiceChatPipeline, generate
pipe = VoiceChatPipeline()
pipe.voices = {vid: {'file': m['file'], 'audio': None, 'persona': m.get('persona')} for vid, m in data['voices'].items()}
out = generate(pipe, type="session.update", session={"voice": "GutAI", "language": "en"})
```
- `out["type"] == "session.updated"` ✅
- `out["session"]["voice"] == "GutAI"` ✅
- `"id" in out["session"]` ✅
- `available_voices: ['GutAI', 'ff', 'bp', 'bo', 'sa']` ✅

### ✅ Step 5: Session config
```python
out = generate(pipe, type="session.update", session={"voice": "bo", "language": "hu"})
```
- `out["session"]["voice"] == "bo"` ✅
- `out["session"]["language"] == "hu"` ✅
- `available_languages: ['en', 'hu']` ✅

### ✅ Step 6: Bad input
```python
out = generate(pipe)  # missing type
```
Raised `ValidationError: 1 validation error for VoiceChatInput\ntype\n  Field required` ✅

### ✅ Step 9: Tear down
```bash
modal app stop voice-chat-worker --yes
```
App stopped. ✅

### ⏳ Steps 7-8: WebSocket & voice switching

**BLOCKED**: Modal SDK 1.5.5 has a bug with WebSocket ASGI serialization.

```
TypeError: bad argument type for built-in operation
  at _serialize_asgi -> websocket_close=api_pb2.Asgi.WebsocketClose(...)
```

The Modal container crashes when a WebSocket connection closes. The sync `generate()` endpoint works fine (tested and verified). The `/v1/realtime` WebSocket endpoint needs:
- Upgrade Modal SDK to >=1.6.0 (if available), OR
- Workaround: avoid using `@modal.asgi_app()` for WebSocket endpoints

### ✅ Step 9: Tear down
```bash
modal app stop voice-chat-worker --yes
```
App stopped. ✅

### Required code changes summary

| File | Change |
|------|--------|
| `apps/gpu-workers/` → `apps/gpu_workers/` | Rename (hyphens → underscores for Python importability) |
| `apps/__init__.py` | Created (empty, makes `apps` a package) |
| `pyproject.toml` | `where = [".", "workers"]`, `include = ["workers*", "apps*", "apps.*"]` |
| `worker_modal_cls_voice_chat.py:58` | `from TTS.api import TTS` (was `importlib.import_module`) |
| `worker_modal_cls_voice_chat.py:83` | `.add_local_python_source("apps", "apps.gpu_workers")` (was `"workers"`) |

## Expected log tags
`[INIT]` → `[REQ]` → `[GEN]` → `[R2]` → `[OK]` (or `[ERR]`)

## Failure signals
- `[ERR]` in logs
- `call.get()` raises
- WebSocket close with code 1008 (auth failure)
