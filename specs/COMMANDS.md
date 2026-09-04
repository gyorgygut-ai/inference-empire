# GPU Worker Commands & Workflow

---

## CLI Tools

### Flash
- Local dev: `flash dev`
- Deploy: `flash deploy` (or `flash deploy --name <name>`)
- Preview: `flash deploy --preview`
- Tear down: `flash undeploy` (or `flash undeploy --name <name>`)

### Beam
- Local dev: `beam serve`
- Deploy: `beam deploy <file>` (or `beam deploy` for all)
- Logs: `beam logs`

### Modal
- Deploy: `modal deploy <file>` (or `modal deploy`)
- Invoke: `modal.Function.from_name("app","method").spawn(...)` (do not use `modal run`)

---

## Worker Management

### Deploy
- Flash: `flash deploy`
- Beam: `beam deploy <file>`
- Modal: `modal deploy <file>`

### Undeploy
- Flash: `flash undeploy`
- Beam: `beam worker stop --name <name>` (or `beam worker stop --all`)
- Modal: `modal app stop <app-name>` (use `stop`, never `destroy`)

### Task Cancellation
- Beam: `beam task list` → `beam task stop <task-id>`
- Beam (all pending): `beam task list | grep PENDING | awk '{print $1}' | xargs beam task stop`
- Modal: N/A (`spawn()` + `.result()` tasks are not independently cancellable)

### Logging & Polling
- Beam single task: `beam logs --task-id <id>`
- Beam worker tasks: `beam logs --stub-id <name>`
- Beam poll async task (for e2e_dev): `beam logs --task-id <id> --timeout 3600 --follow` (wait for `[OK]` or `[ERR]`)
- Modal app logs: `modal app logs <app-name>`
- Modal container logs: `modal container logs <container-id>`

Log tag order: `[INIT]` → `[REQ]` → `[GEN]` → `[R2]` → `[OK]` (or `[ERR]`).

---

## Testing

### Run All Tests
- Fake (mocked inference, local): `python -m pytest workers/ --target fake`
- Per model: `python -m pytest workers/<model>/tests/ --target fake`
- `--target live` runs are owner-operated only, never part of this repo's execution.

### Run Per-Worker Tests
- Single worker: `python -m pytest workers/<model>/tests/test_<worker-name>.py --target fake -k "<test>"`

### Test Lifecycle
```
fake (mocked inference, local) — live runs are owner-operated, outside this plan.
```
No proceeding to next level without previous level passing.

### E2E Dev Pattern
1. Deploys test worker before all tests (`setup_module`)
2. Runs tests against deployed endpoint
3. Undeploys after all tests (`teardown_module`)
