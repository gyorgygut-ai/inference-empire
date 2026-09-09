# GUI Agent Implementation Spec

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

## App Context

- Next.js app with assistant-ui
- Inference via proxy to hide API keys
- TypeScript
- ESLint
- shadcn/ui Radix flavor
- Tailwind v4

## UI Layout

Mobile:

- left Workers: dockable, docked closed by default
- center: Main
- right Artifacts: dockable, docked closed by default

Desktop:

- left Workers: dockable, open by default, next to Main chat
- right Artifacts: fills remaining space

## Worker → Chat Mapping

- `vision` `small_vision` — sync direct handler only — image attachment → JSON `classification/subjects/description` inline — no extra boxes
- `flux2` `flux2_klein9b` — both: **(a) direct handler** (no LLM) context `flux` boxes: height/width/guidance_scale/steps/seed/reference_images + prompt → image `presigned_url` → Artifacts **(b) LLM tool-call** `flux2_klein9b` tool with same inputs → image `presigned_url` → Artifacts — per `flux2_klein9b.json:4-14`
- `krea2` `krea2_ref2img` — both: **(a) direct** context `krea` boxes: height/width/steps/guidance_scale/seed/lora_scale/face_crop/reference_image + prompt **(b) tool-call** `krea2_ref2img` — same `krea2_ref2img.json:8-14` → image `presigned_url`
- `h3` `minimax_h3_comfy` — **(a) direct** context `h3` boxes: width/height/length/steps/seed/first_frame/last_frame **(b) tool-call** `h3_comfy` — per `minimax_h3_comfy.json:12-13` → video `presigned_url` + `video` base64
- `h3-ref` `minimax_h3_turbo_ref2va` — **(a) direct** context `h3-ref` boxes: ref_images(≤9)/ref_videos(≤3)/ref_audios(≤3) + width/height/length/steps/seed **(b) tool-call** `h3_turbo_ref2va` — per `minimax_h3_turbo_ref2va.json` → video `presigned_url`
- `voice` `realtime_voice_*` — ASGI stream `audio.delta` (v2) — not in this cut

## State

- No persistence after page refresh for v1

## Coding Style & Standards

- Mirror face-value rules: no semicolons (`semi: ["error", "never"]`), no kindergarten-level comments, ESLint rules non-negotiable.
