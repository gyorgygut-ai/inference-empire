import importlib


def _assert_image_environment(monkeypatch, module_name, expected):
    for name, value in expected.items():
        monkeypatch.setenv(name, value)
    module = importlib.import_module(module_name)
    importlib.reload(module)
    configured = dict(line.split("=", 1) for line in module.image.env_vars)
    assert all(configured.get(name) == value for name, value in expected.items())


def test_inference_workers_receive_schema_huggingface_token(monkeypatch):
    expected = {"SECRET_HUGGINGFACE_TOKEN": "hf-sentinel"}
    _assert_image_environment(
        monkeypatch, "worker_voice_llm_chat_completions_beam", expected
    )
    _assert_image_environment(
        monkeypatch, "worker_voice_stt_audio_transcriptions_beam", expected
    )
    _assert_image_environment(
        monkeypatch, "worker_voice_tts_audio_speech_beam", expected
    )


def test_realtime_worker_receives_schema_api_keys_and_endpoints(monkeypatch):
    expected = {
        "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY": "stt-key-sentinel",
        "STT_AUDIO_TRANSCRIPTIONS_API_TOKEN": "https://stt.invalid",
        "GENERATED_LLM_CHAT_COMPLETIONS_API_KEY": "llm-key-sentinel",
        "LLM_CHAT_COMPLETIONS_API_TOKEN": "https://llm.invalid",
        "GENERATED_TTS_AUDIO_SPEECH_API_KEY": "tts-key-sentinel",
        "TTS_AUDIO_SPEECH_API_TOKEN": "https://tts.invalid",
    }
    _assert_image_environment(
        monkeypatch, "worker_voice_realtime_session_beam", expected
    )
