def test_success(modal_cls, storage):
    worker = modal_cls.create_worker(storage=storage)
    out = modal_cls.run(worker, storage=storage, image_base64="ZmFrZQ==")
    assert out["classification"] == "object_0p"


def test_failure(modal_cls, storage):
    import pytest as _p

    worker = modal_cls.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: modal_cls.run(worker, storage=storage, image_base64="failure"))
