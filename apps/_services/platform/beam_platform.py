"""Real Beam platform. Owner-operated live path only."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps._services.platform.spec import WorkerSpec


class BeamPlatform:
    def __init__(self, worker_factory=None):
        self._worker_factory = worker_factory
        self._spec: WorkerSpec | None = None

    def _handler(self):
        assert self._spec is not None
        # "file:function" — beam deploys the decorated attr from the module.
        path = Path(*self._spec.module.split(".")).with_suffix(".py")
        return f"{path}:{self._spec.attr}"

    def deploy(self):
        subprocess.run(["beam", "deploy", self._handler()], check=True)

    def undeploy(self):
        assert self._spec is not None
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
