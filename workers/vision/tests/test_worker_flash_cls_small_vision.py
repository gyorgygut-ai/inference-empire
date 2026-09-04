def test_success(flash_cls, storage):
    worker = flash_cls.create_worker(storage=storage)
    out = flash_cls.run(worker, storage=storage, image_base64="ZmFrZQ==")
    assert out["classification"] == "object_0p"


def test_failure(flash_cls, storage):
    import pytest as _p

    worker = flash_cls.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: flash_cls.run(worker, storage=storage, image_base64="failure"))
