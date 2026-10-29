from __future__ import annotations

from typing import Any


class FakeTorchModule:
    """Fake torch module for testing."""

    class Generator:
        def __init__(self, device: str = "cpu"):
            self.device = device

        def manual_seed(self, _seed: int) -> FakeTorchModule.Generator:
            return self

    class _Cuda:
        def is_available(self) -> bool:
            return False

    cuda = _Cuda()

    def bfloat16(self) -> Any:
        return "fake_bfloat16"
