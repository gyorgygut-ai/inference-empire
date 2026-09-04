# Testing Checklist

## GPU Workers

**Test + Code Rules**:

- Use `pytest` + `tests` folder
- One test file per worker
- Each worker file must have e2e tests
- Any worker change must result in a failing test
- Tests focus on set input -> expected output
- Keep test code stupid; aim to avoid mocking & magic
- Task finished when tests pass, without shortcuts
- Mock side effects in local e2e; inference, external API calls; DI is the pattern
- Same test file for fake and live targets

**E2E Tests**:

Tests are run with `--target fake` (local, mocked adapters) or `--target live` (dev, real adapters).

### Sync (Flash `cls`, `pre`, Beam `eq`)

- [ ] generate(): invalid input -> rejects
- [ ] generate(): good input -> inference fail -> returns output contract
- [ ] generate(): good input -> inference success -> returns output contract
- [ ] generate(): good input -> inference success -> uploads artifact

### Async (Beam `tq`, Beam `asgi`, Modal `cls` with `spawn()`)

- [ ] generate(): invalid input -> rejects (before task submitted)
- [ ] POST -> task_id -> poll -> returns error contract
- [ ] POST -> task_id -> poll -> returns output contract
- [ ] POST -> task_id -> poll -> uploads artifact
