def test_speech(beam_asgi, storage):
    worker = beam_asgi.create_worker(storage=storage)
    out = beam_asgi.run(worker, storage=storage, type="speech", input="hello")
    assert out["content_type"] == "audio/wav"
    assert out["audio"]


def test_failure(beam_asgi, storage):
    import pytest as _p

    worker = beam_asgi.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: beam_asgi.run(worker, storage=storage, type="failure"))
