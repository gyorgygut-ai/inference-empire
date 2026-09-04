def test_success(beam_tq, storage):
    worker = beam_tq.create_worker(storage=storage)
    out = beam_tq.run(worker, storage=storage, prompt="cat")
    assert "artifact" in out


def test_failure(beam_tq, storage):
    import pytest as _p

    worker = beam_tq.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: beam_tq.run(worker, storage=storage, prompt="failure"))


def test_async_poll(beam_tq, storage):
    worker = beam_tq.create_worker(storage=storage)
    tid = beam_tq.submit(worker, storage=storage, prompt="cat")
    assert beam_tq.poll(tid) in ("IN_PROGRESS", "COMPLETED")
    out = beam_tq.result(tid)
    assert "artifact" in out
