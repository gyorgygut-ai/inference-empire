"""Send 10 parallel image generation requests via Modal workers and verify in R2."""
import sys, os, time
import modal, boto3

PROMPTS = [
    ("flux2_1", "A cyberpunk samurai standing on a neon-lit rooftop overlooking a rain-soaked Tokyo at night"),
    ("flux2_2", "A giant mechanical whale swimming through a cloud-filled sky above a Victorian city"),
    ("flux2_3", "An enchanted forest with bioluminescent mushrooms and floating fairy lights at twilight"),
    ("flux2_4", "A steampunk airship flying over a vast desert with ancient ruins below"),
    ("flux2_5", "A cozy library with floating books and golden dust particles in warm lamplight"),
    ("krea2_1", "A portrait of a young woman with flowing red hair standing in a field of lavender at sunset"),
    ("krea2_2", "An elegant elf warrior in silver armor standing on a cliff overlooking an ocean storm"),
    ("krea2_3", "A cyberpunk hacker in a neon-lit alley with holographic advertisements"),
    ("krea2_4", "A princess in a golden ball gown dancing in a crystal palace with chandeliers"),
    ("krea2_5", "A street artist painting a vibrant mural on a graffiti-covered brick wall"),
]

flux2_cls = modal.Cls.from_name("flux2-klein9b-worker", "FluxKleinWorker")
krea2_cls = modal.Cls.from_name("krea2-ref2img-worker", "Krea2Ref2ImgWorker")

print("=" * 70)
print("SENDING 10 IMAGE GENERATION REQUESTS VIA MODAL WORKERS")
print("=" * 70)

results = {}

print("\n[FLUX2] Sending 5 requests...")
for key, prompt in PROMPTS[:5]:
    print(f"  → {key}: {prompt[:60]}...")
    instance = flux2_cls()
    try:
        result = instance.generate.remote(prompt=prompt, height=512, width=512, guidance_scale=1.0, num_inference_steps=4)
        results[key] = {"status": "done", "data": result}
        print(f"    ✓ Done")
    except Exception as e:
        results[key] = {"status": f"ERROR: {e}"}
        print(f"    ✗ {e}")
    time.sleep(1)

print("\n[KREA2] Sending 5 requests...")
for key, prompt in PROMPTS[5:]:
    print(f"  → {key}: {prompt[:60]}...")
    instance = krea2_cls()
    try:
        result = instance.generate.remote(prompt=prompt)
        results[key] = {"status": "done", "data": result}
        print(f"    ✓ Done")
    except Exception as e:
        results[key] = {"status": f"ERROR: {e}"}
        print(f"    ✗ {e}")
    time.sleep(1)

# Check R2
print("\n" + "=" * 70)
print("CHECKING R2 BUCKET FOR GENERATED IMAGES")
print("=" * 70)

endpoint = os.environ["R2_ENDPOINT"]
access_key = os.environ["R2_ACCESS_KEY"]
secret_key = os.environ["R2_SECRET_KEY"]

s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
resp = s3.list_objects_v2(Bucket="generated-media", Prefix="", MaxKeys=100)

flux2_files = sorted([o for o in resp.get("Contents", []) if o["Key"].startswith("flux2_")], key=lambda x: x["Key"])
krea2_files = sorted([o for o in resp.get("Contents", []) if o["Key"].startswith("krea2_")], key=lambda x: x["Key"])

print(f"\nFlux2 images in R2: {len(flux2_files)}")
for f in flux2_files:
    print(f"  ✓ {f['Key']} ({f['Size']} bytes)")
print(f"\nKrea2 images in R2: {len(krea2_files)}")
for f in krea2_files:
    print(f"  ✓ {f['Key']} ({f['Size']} bytes)")

# Verify
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

all_ok = True
for key, info in results.items():
    prefix = "flux2" if key.startswith("flux2") else "krea2"
    files = flux2_files if prefix == "flux2" else krea2_files
    has_artifact = len(files) > 0 and info["status"] == "done"
    char = "✓" if has_artifact else "✗"
    msg = "OK" if has_artifact else f"FAILED: {info.get('status', 'unknown')}"
    print(f"  {char} {key}: {msg}")
    if not has_artifact:
        all_ok = False

print(f"\n{'=' * 70}")
print(f"RESULT: {'ALL 10 REQUESTS SUCCESSFUL' if all_ok else 'SOME REQUESTS FAILED'}")
print(f"{'=' * 70}")

sys.exit(0 if all_ok else 1)