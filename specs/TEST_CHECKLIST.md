# Testing Checklist

## GPU Workers

**Test + Code Rules**:

- Use `pytest` + `tests` folder
- One test file per test type per worker
- Each worker file must have unit and e2e tests
- Any worker change must result in a failing test
- Tests focus on set input -> expected output
- Keep test code stupid; aim to avoid mocking & magic
- Task finished when tests pass, without shortcusts
- No proceeding until level passed; unit < e2e (local) > e2e (dev)
- Mock side effects in unit and local e2e; inference, external API calls; DI is the pattern

**Unit Tests**:

- [ ] generate(): invalid input -> rejects
- [ ] generate(): good input -> inference fail -> returns output contract
- [ ] generate(): good input -> inference success -> returns output contract
- [ ] generate(): good input -> inference success -> uploads artifact

**E2E Tests (local, isolated)**:

- [ ] generate(): invalid input -> rejects
- [ ] generate(): good input -> inference fail -> returns output contract
- [ ] generate(): good input -> inference success -> returns output contract
- [ ] generate(): good input -> inference success -> uploads artifact

**E2E Tests (dev)**:

Test code deploys test worker before all; undeploys after all.

- [ ] generate(): good input -> returns output contract, R2 bucket has artifact
