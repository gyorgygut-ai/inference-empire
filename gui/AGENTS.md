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

## State

- No persistence after page refresh for v1

## Coding Style & Standards

- Mirror face-value rules: no semicolons (`semi: ["error", "never"]`), no kindergarten-level comments, ESLint rules non-negotiable.
