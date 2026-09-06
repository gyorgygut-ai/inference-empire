# Local E2E Tiny — real small models, production output types

## Goal
Tiny loaders return REAL inference in production types so `generate()`
needs no change. No canned in e2e.

## New
- `workers/services/inference/tiny_image.py` — `segmind/tiny-sd`, real PIL.
  `import torch` inside function body.
- `workers/services/inference/tiny_vision.py` — `auge --output json` + `apfel`,
  real dict vs `contracts/*.json`.
- `workers/services/inference/tiny_video.py` — `ByteDance/AnimateDiff-Lightning`
  on tiny-sd, real mp4; ffmpeg fallback so artifact check stays real.
- Sizes/steps/frames decided at implementation, not locked here.

## Order
Vision → Flux2 → Krea2 → H3, one green before next.

## Verify
- `python -m pytest workers/vision/tests/ --target fake -x -q`
- `python -m pytest workers/flux2/tests/ --target fake -x -q`
- `python -m pytest workers/krea2/tests/ --target fake -x -q`
- `python -m pytest workers/h3/tests/ --target fake -x -q`
