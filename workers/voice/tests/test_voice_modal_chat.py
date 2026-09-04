from workers.voice.testing import VOICE_CHAT_MODAL_ASGI as SPEC


def test_session_created(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    evt = runner.run(worker, type="session.update", session={})
    assert evt["type"] in ("session.created", "session.updated", "error")


def test_failure(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(worker, type="failure")
        assert False, "Should raise"
    except RuntimeError as e:
        assert "inference failed" in str(e)
