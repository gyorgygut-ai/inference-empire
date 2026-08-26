# Testing + Coding

**Test + Code Rules**:

- Use `pytest` + `tests` folder
- One test file per test type per worker
- Each worker file must have unit and e2e tests
- Any worker change must result in a failing test
- Tests focus on set input -> expected output
- Keep test code stupid; aim to avoid mocking & magic
- Task finished when tests pass, without shortcusts
- No proceeding until level passed; unit < e2e (local) > e2e (dev)

**Unit Tests**:

- Be minimalistic, yet sufficient; just enough is enough
- Test input: none, invalid, good but failed, good and succeeded
- Stub side effects; inference, external API calls; DI is the pattern

**E2E Tests (local, isolated)**:

- Replicate env of provider in Docker (Dockerfiles on Github)
- Each test does docker up, test, docker down; no need to get smart
- Test input: none, invalid, good but failed, good and succeeded
- Stub side effects, assert for them; inference, external API calls; DI is the pattern

**E2E Tests (dev)**:

- Deploy a dev / test endpoint; undeploy it after
- Invoke the deployed endpoint just like in real life
- Tests: quick smoke (ping), good input (sunny)
- Test real side effects like webhooks, artifact uploads
