class FakeFlashPlatform:
    def __init__(self, worker_factory=None):
        self._worker_factory = worker_factory

    def deploy(self):
        pass

    def undeploy(self):
        pass

    def create_worker(self, storage):
        return self._worker_factory(storage=storage) if self._worker_factory else None
