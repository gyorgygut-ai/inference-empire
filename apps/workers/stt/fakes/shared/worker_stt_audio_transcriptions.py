import os

from fastapi import FastAPI, File, HTTPException, Request, UploadFile


def build_app() -> FastAPI:
    app = FastAPI(title="worker-stt-local-stub")
    expected_token = os.environ.get("SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY", "")
    request_count = 0

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__test__/metrics")
    def metrics() -> dict[str, int]:
        return {"requests": request_count}

    @app.post("/__test__/reset")
    def reset_metrics() -> dict[str, int]:
        nonlocal request_count
        request_count = 0
        return {"requests": request_count}

    @app.post("/v1/audio/transcriptions")
    async def transcribe(request: Request, file: UploadFile = File(...)) -> dict[str, str]:
        nonlocal request_count
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        if scheme.casefold() != "bearer" or not expected_token or supplied != expected_token:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if not await file.read():
            raise HTTPException(status_code=422, detail="Audio file is empty")
        request_count += 1
        return {"text": "Hello, this is a local voice-turn stub."}

    return app
