"""Cerebrium Cortex entrypoint for krea2-ref2img.

Cerebrium requires main.py; this file delegates to the actual worker logic.
"""
from __future__ import annotations

from worker_krea2_cerebrium import run

__all__ = ["run"]

if __name__ == "__main__":
    import json
    import sys
    result = run(json.loads(sys.stdin.read()))
    print(json.dumps(result))
