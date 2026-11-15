"""Cerebrium Cortex entrypoint for flux2-klein9b.

Cerebrium requires main.py; this file delegates to the actual worker logic.
"""
from __future__ import annotations

from worker_flux2_cerebrium import generate

__all__ = ["generate"]

if __name__ == "__main__":
    import json
    import sys
    result = generate(**json.loads(sys.stdin.read()))
    print(json.dumps(result))
