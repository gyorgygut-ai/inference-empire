# GUI Agent Implementation Spec

## Critical Specs - Read Before Doing Anything

- [GUI and CLI](../specs/GUI_AND_CLI.md)
- [Proxy](../specs/PROXY.md)
- [GPU Workers](../specs/GPU_WORKERS.md)
- [Testing Checklist](../specs/TEST_CHECKLIST.md)

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
- center: assistant-ui chat
- right Artifacts: dockable, docked closed by default

Desktop:
- breakpoint to be determined
- left Workers: dockable, open by default, next to assistant-ui chat
- right Artifacts: fills remaining space

## Constraints

- Workers and Artifacts render component names as hardcoded strings for v1
