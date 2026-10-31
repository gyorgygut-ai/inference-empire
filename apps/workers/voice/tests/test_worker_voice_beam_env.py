import importlib


def _assert_image_environment(monkeypatch, module_name, expected):
    for name, value in expected.items():
        monkeypatch.setenv(name, value)
    module = importlib.import_module(module_name)
    importlib.reload(module)
    configured = dict(line.split("=", 1) for line in module.image.env_vars)
    assert all(configured.get(name) == value for name, value in expected.items())


def test_inference_workers_receive_schema_huggingface_token(monkeypatch):
    workers = (
        (
            "worker_voice_stt_audio_transcriptions_beam",
            "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY",
        ),
        ("worker_voice_llm_chat_completions_beam", "GENERATED_LLM_CHAT_COMPLETIONS_API_KEY"),
        ("worker_voice_tts_audio_speech_beam", "GENERATED_TTS_AUDIO_SPEECH_API_KEY"),
    )
    for module, api_key in workers:
        _assert_image_environment(
            monkeypatch,
            module,
            {"SECRET_HUGGINGFACE_TOKEN": "hf-sentinel", api_key: "service-key-sentinel"},
        )


def test_realtime_worker_receives_schema_api_keys_and_endpoint_urls(monkeypatch):
    expected = {
        "GENERATED_VOICE_WORKER_AUTH_TOKEN": "worker-auth-sentinel",
        "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY": "stt-key-sentinel",
        "STT_AUDIO_TRANSCRIPTIONS_API_URL": "https://stt.invalid",
        "GENERATED_LLM_CHAT_COMPLETIONS_API_KEY": "llm-key-sentinel",
        "LLM_CHAT_COMPLETIONS_API_URL": "https://llm.invalid",
        "GENERATED_TTS_AUDIO_SPEECH_API_KEY": "tts-key-sentinel",
        "TTS_AUDIO_SPEECH_API_URL": "https://tts.invalid",
    }
    _assert_image_environment(monkeypatch, "worker_voice_realtime_session_beam", expected)
