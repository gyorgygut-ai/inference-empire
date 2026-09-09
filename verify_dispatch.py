import sys
import traceback
from workers.h3 import worker_beam_tq_minimax_h3_comfy as worker_mod

params = dict(
    prompt="a red square",
    width=1344,
    height=768,
    length=48,
    steps=20,
    seed=42,
)

print("Submitting task...")
try:
    task = worker_mod.dispatch.put(**params)
    print("Task submitted, waiting up to 120s...")
    out = task.result(wait=True, timeout=120)
    print("Result:", out)
    if out and out.get("artifact", {}).get("presigned_url"):
        print("SUCCESS: artifact URL present")
    else:
        print("FAIL: no artifact")
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
    sys.exit(1)
