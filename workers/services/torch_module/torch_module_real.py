from __future__ import annotations

import torch


class RealTorchModule:
    """Real torch module that applies necessary patches for certain environments."""

    def __init__(self):
        import torch.distributed as dist

        dist.is_available = lambda: False

    def get(self):
        return torch
