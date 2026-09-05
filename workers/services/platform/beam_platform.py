"""Real Beam platform. Owner-operated live path only."""

import json
import subprocess
from pathlib import Path


class RealBeamPlatform:
    def __init__(self, worker_factory=None):
        self._worker_factory = worker_factory
        self._spec = None

    def _handler(self):
        # "file:function" — beam deploys the decorated attr from the module.
        path = Path(*self._spec.module.split(".")).with_suffix(".py")
        return f"{path}:{self._spec.attr}"

    def deploy(self):
        subprocess.run(["beam", "deploy", self._handler()], check=True)

    def undeploy(self):
        # Delete takes a DEPLOYMENT_ID, not a name: resolve via list.
        out = subprocess.run(
            ["beam", "deployment", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        for dep in json.loads(out.stdout):
            name = dep.get("name") or dep.get("deployment_name", "")
            if name == self._spec.live_endpoint:
                subprocess.run(
                    ["beam", "deployment", "delete", dep["id"]], check=True
                )
                return
        print(f"[beam] no deployment named {self._spec.live_endpoint!r}; skipping")

    def create_worker(self, storage):
        return self._worker_factory(storage=storage) if self._worker_factory else None
