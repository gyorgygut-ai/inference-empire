from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerSpec:
    module: str
    attr: str
    live_endpoint: str
    shape: str
    input_model: object = None
    extra: dict = field(default_factory=dict)
