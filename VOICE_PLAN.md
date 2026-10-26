# Voice Workers Verification Plan

**Start with this**:

- Activate all modal, gpu cloud worker related skills
- Activate python-uv, ty skills, nx-run-tasks skills

**Rules**:

- No guessing, no shortcuts, no cheats
- DO NOT go to next project until current is not proven 100%
- DO NOT go to next tier until current is not proven 100%

## Workflow Tiers

**1. Discovery**:
  - Details described per project
  - Do gap analysis on the project folder
  - Do static verification, lint, typecheck on the project folder

**2. Suggest**:
  - List each found flaw, with: short description, suggestion to fix, cited proof of why that fix
  - Provide code preview of key touches
  - Add a verification proof steps plan to each suggestion

**3. Non-negotiable proofs**:

  - Run verification, deploy in foreground; deploy must succeed without error
  - Send a real request to deployed worker; all turns, responses, request must work flawlessly
  - Prepare a plan for providing actual material proof of the exchange succeeding

## 1. Project: apps/workers/fastrtc_voice

  DO NOT build any frontend ui. This is a worker plan only.

  **1. Discovery**:
    - READ this when reviewing the implementation: do web search for official docs of used tooling

## 2. Project: apps/workers/voice

  DO NOT build any frontend ui. This is a worker plan only.

  **1. Discovery**:
    - READ this when reviewing the implementation: do web search for official docs of used tooling
  
## 3. Project: apps/workers/realtime_voice

  DO NOT build any frontend ui. This is a worker plan only.

  **1. Discovery**:
    - READ this when reviewing the implementation: do web search for official docs of used tooling
