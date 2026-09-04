from __future__ import annotations

import os

from workers.services.torch_module.torch_module_fake import FakeTorchModule
from workers.services.torch_module.torch_module_real import RealTorchModule


def torch_module_factory(target: str | None = None) -> RealTorchModule | FakeTorchModule:
    if target is None:
        target = os.environ.get("TORCH_TARGET", "real")
    if target == "fake":
        return FakeTorchModule()
    if target == "real":
        return RealTorchModule()
    raise ValueError(f"unknown torch target: {target!r}")
