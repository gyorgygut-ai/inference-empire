"""Verification script for H3-FL2VA-COMFY Beam worker via beam shell.
Run inside beam shell container for workers/h3/worker_beam_tq_minimax_h3_comfy.py:dispatch
"""

import workers.h3.worker_beam_tq_minimax_h3_comfy as worker_mod

print("[STEP] Loading dependencies...")
storage, comfy_base_url = worker_mod.load_dependencies()
print(f"[INIT] comfy_base_url={comfy_base_url}")

PROMPT = (
    "A smooth cinematic dolly shot across a futuristic neon city at night, "
    "rain reflecting lights on wet streets, photorealistic, shallow depth of field"
)

params = dict(
    prompt=PROMPT,
    width=1344,
    height=768,
    length=48,   # 2 seconds @ 24fps
    steps=20,
    seed=42,
)

print(f"[REQ] Running generate with params: {params}")
out = worker_mod.generate(storage, comfy_base_url, **params)

print("[OK] Output:", out)

presigned = out.get("artifact", {}).get("presigned_url")
if not presigned:
    raise RuntimeError("Missing presigned_url in output")

print(f"[R2] Artifact URL: {presigned}")
print("[DONE] Verification complete")
