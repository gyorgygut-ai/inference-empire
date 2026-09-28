from __future__ import annotations

from typing import Protocol


class TorchModule(Protocol):
    """Provides access to the torch module."""

    def __getattr__(self, name: str) -> object: ...
