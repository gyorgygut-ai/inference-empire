def test_session_created(beam_asgi, storage):
    worker = beam_asgi.create_worker(storage=storage)
    evt = beam_asgi.run(worker, storage=storage, type="session.update", session={})
    assert evt["type"] in ("session.created", "session.updated", "error")


def test_failure(beam_asgi, storage):
    import pytest as _p

    worker = beam_asgi.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: beam_asgi.run(worker, storage=storage, type="failure"))
