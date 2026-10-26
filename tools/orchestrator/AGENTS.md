# Orchestrator

**orchestrator:run-command**:

- **Problem**: `task-abc` needs runtime values from a contract 
- **Contract**: `gateway-dev` -> `{ SECRET_KEY -> command, RAND_ID -> command }`)
- **Trigger**: `task-abc` declares `packages/contracts/gateway-dev.contract.ts` as `input`
- **Reaction**: values resolved invoking each `command`; `inputs` extended with `env`
- **Outcome**: `task-abc` can access and is `affected` by `process.env.SECRET_KEY,RAND_ID`;

- **Acceptance**:
  - `executor` detects contract `inputs`
  - `executor` resolved contract `values`
  - `executor` throws if there is no `value`
  - `consumer` receives values in `process.env`
  - `contract` value changes affect; nx selects tasks

**Scripts**:

- **get-beam-url <app-name>**: `tools/orchestrator/src/get-beam-url.ts workers-flux2`
- **get-modal-url <app-name> [function-name=generate_web]**: `tools/orchestrator/src/get-modal-url.ts workers-flux2`
- **get-flash-url <endpoint-name> [--dir <flash-project-dir>]**: `tools/orchestrator/src/get-flash-url.ts workers-flux2 --dir apps/workers/flux2/dist/flash`
- **get-netlify-url <site-id>**: `tools/orchestrator/src/get-netlify-url.ts cd41f060-bbdf-49fa-82a6-20d7ba136853`
- **get-vercel-url <project-id> [--org <team-id>]**: `tools/orchestrator/src/get-vercel-url.ts prj_JKvkpSDegXCmwbFYBcz6enzo1bK5 --org team_J6vdHfx7Bjz7VVskbtdbL8kq`
