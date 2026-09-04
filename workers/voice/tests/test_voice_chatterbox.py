from workers.voice.testing import VOICE_CHATTERBOX_BEAM_ASGI as SPEC


def test_speech_returns_audio(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    result = runner.run(worker)
    assert result["status_code"] == 200
    assert result["content_len"] > 0


def test_failure(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(worker, type="failure")
        assert False, "Should raise"
    except RuntimeError as e:
        assert "inference failed" in str(e)
