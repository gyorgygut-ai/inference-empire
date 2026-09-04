from __future__ import annotations

from typing import Any


class FakeTorchModule:
    """Fake torch module for testing."""

    class Generator:
        def manual_seed(self, seed: int) -> FakeTorchModule.Generator:
            return self

    def bfloat16(self) -> Any:
        return "fake_bfloat16"

    def cuda(self) -> bool:
        return False

    def is_available(self) -> bool:
        return False
