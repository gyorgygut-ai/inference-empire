def test_success(flash_cls, storage):
    worker = flash_cls.create_worker(storage=storage)
    out = flash_cls.run(worker, storage=storage, prompt="a cat")
    assert "artifact" in out


def test_failure(flash_cls, storage):
    import pytest as _p

    worker = flash_cls.create_worker(storage=storage)
    _p.raises(RuntimeError, lambda: flash_cls.run(worker, storage=storage, prompt="failure"))
