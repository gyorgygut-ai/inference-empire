# Testing Checklist

## GPU Workers

**Test + Code Rules**:

- Use `pytest` + `tests` folder
- One test file per worker
- Each worker file must have e2e tests
- Any worker change must result in a failing test
- Tests focus on set input -> expected output
- Keep test code stupid; aim to avoid too much mocking & magic
- Task finished when tests pass, without shortcuts

## Unit Tests

**Rules**:

- Tests-first worker architecture with `_shared_*` file in worker folder
- `load_dependencies` and `do_inference` always used from shared
- `load_dependencies` mocked with fakes to avoid side effects

**Cases**:

- [ ] Inference requested with right args
- [ ] Fake bucket has "uploaded" artifact
- [ ] `do_inference` returns output contract

## E2E Tests

**Rules**:

- E2E tests kept minimal, because they are slow
- With a distinct pytest fixture per type
- Sync (Flash `cls`, `pre`, Beam `eq`) direct response
- Async (Beam `tq`, Beam `asgi`, Modal `cls` with `spawn()`) task_id polling

**Tests**:

- [ ] Worker deployed to test env in before ALL, undeployed after tests
- [ ] Invalid input: should reject
- [ ] Good input: should return contract + artifact must exist in bucket (if applicable)
