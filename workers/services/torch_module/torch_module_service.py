from __future__ import annotations

import torch


class TorchModuleService:
    """Service torch module: applies necessary patches for certain
    environments, delegates everything else to real torch."""

    def __init__(self):
        import torch.distributed as dist

        dist.is_available = lambda: False

    def __getattr__(self, name: str):
        return getattr(torch, name)
