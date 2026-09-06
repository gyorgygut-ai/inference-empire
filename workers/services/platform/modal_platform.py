"""Real Modal platform. Owner-operated live path only."""

import subprocess
from pathlib import Path


class ModalPlatform:
    def __init__(self, worker_factory=None):
        self._worker_factory = worker_factory
        self._spec = None

    def _worker_file(self):
        return str(Path(*self._spec.module.split(".")).with_suffix(".py"))

    def deploy(self):
        subprocess.run(["modal", "deploy", self._worker_file()], check=True)

    def undeploy(self):
        subprocess.run(["modal", "app", "stop", self._spec.live_endpoint], check=True)

    def create_worker(self, storage):
        return self._worker_factory(storage=storage) if self._worker_factory else None
