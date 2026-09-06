"""Real Flash platform. Owner-operated live path only."""

import subprocess
from pathlib import Path


class FlashPlatform:
    def __init__(self, worker_factory=None):
        self._worker_factory = worker_factory
        self._spec = None

    def _worker_dir(self):
        # spec.module = "workers.<model>.worker_..." -> workers/<model>/
        return Path(*self._spec.module.split(".")[:2])

    def deploy(self):
        # Project-level deploy; .flash/ envs live in the worker dir.
        subprocess.run(["flash", "deploy"], cwd=self._worker_dir(), check=True)

    def undeploy(self):
        subprocess.run(
            ["flash", "undeploy", self._spec.live_endpoint],
            cwd=self._worker_dir(),
            check=True,
        )

    def create_worker(self, storage):
        return self._worker_factory(storage=storage) if self._worker_factory else None
