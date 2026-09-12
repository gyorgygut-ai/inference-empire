# Sync — manifest single source (Workers + Chat)

## Script
- `scripts/build-manifest.mjs` (in `gui/scripts/`) — reads only `../workers/**/worker_*.py` (`worker_{beam|flash|modal}_{tq|cls|eq|asgi}_{model}.py` per `../workers/AGENTS.md:26-37`) → writes `src/lib/manifest.json`
- Stem alone gives provider + contract key (`model` → `../workers/{folder}/contracts/{model}.json` exists per glob, verified `flux2_klein9b`, `krea2_ref2img`, `small_vision`, `minimax_h3_*`); no markdown or extra reads

## Consumers
- `src/components/panels/Workers.tsx:9-21` (accordions `vision|flux2|krea2|h3|voice`) reads `manifest.json`
- `src/components/panels/Main.tsx:8-35` model selector contexts (`flux|krea|h3|h3-ref|vision`) reads same `manifest.json`
- Single source of truth — tabs stay in sync

## Runs on
- `package.json:5` `prebuild` → `node scripts/build-manifest.mjs`
- `package.json:5` `predev` → same `node scripts/build-manifest.mjs`
- No handling for list change after build — snapshot at build/dev start only

## Manifest — minimal (serves both Workers + Chat, no redundancy)

```json
{
  "workers": [
    {
      "stem": "worker_beam_tq_flux2_klein9b",
      "platform": "beam",
      "pattern": "tq",
      "model": "flux2_klein9b",
      "inputs": {
        "required": ["prompt"],
        "fields": {
          "prompt": { "default": null },
          "height": { "default": 512 },
          "width": { "default": 512 },
          "guidance_scale": { "default": 1.0 },
          "num_inference_steps": { "default": 4 },
          "seed": { "default": null },
          "reference_images": { "default": [] }
        }
      }
    },
    {
      "stem": "worker_flash_cls_flux2_klein9b",
      "platform": "flash",
      "pattern": "cls",
      "model": "flux2_klein9b",
      "inputs": {
        "required": ["prompt"],
        "fields": {
          "prompt": { "default": null },
          "height": { "default": 512 },
          "width": { "default": 512 },
          "guidance_scale": { "default": 1.0 },
          "num_inference_steps": { "default": 4 },
          "seed": { "default": null },
          "reference_images": { "default": [] }
        }
      }
    },
    {
      "stem": "worker_beam_tq_small_vision",
      "platform": "beam",
      "pattern": "tq",
      "model": "small_vision",
      "inputs": {
        "required": ["image_base64"],
        "fields": { "image_base64": { "default": null } }
      }
    }
  ]
}
```

Workers needs `stem/platform/pattern/model` per worker (accordions + chips + status) — one entry per `stem`, not per `model` (same `model` appears on multiple platforms, e.g. `flux2_klein9b` on `beam/tq` and `flash/cls` are distinct workers); Chat needs `model -> inputs.required/fields.default/maxItems` (context-specific boxes `flux|krea|h3|h3-ref|vision` only when that model picked). No `contract`, `generatedAt`, `type`, `x-rules` — minimal. Trimmed to 3 of ~22 for preview (first two share `model` to show worker distinctness); full has all workers.

## Files when built
- new `scripts/build-manifest.mjs`
- new `src/lib/manifest.json`
- edit `package.json` add `prebuild`/`predev` hooks
