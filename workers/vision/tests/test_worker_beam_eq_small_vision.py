def test_success(beam_eq, storage):
    worker = beam_eq.create_worker(storage=storage)
    out = beam_eq.run(worker, storage=storage, image_base64="ZmFrZQ==")
    assert out["classification"] == "object_0p"


def test_failure(beam_eq, storage):
    import pytest as _p

    worker = beam_eq.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: beam_eq.run(worker, storage=storage, image_base64="failure"))
