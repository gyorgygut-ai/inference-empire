# GPU Workers

**Families**: `flux2`, `krea2`, `tiny_sd`, `vision`, `h3_comfy`, `h3_fl2va`, `h3_ref2va`, `realtime_voice` (`apps/{model}`)
**Schema**: `packages/schemas/{model}/schema.json`

---

## NX: `workers-{family}:deploy-{platform}`

**MUST DO before `:deploy-modal`**:

  - **Build** must build `{projectRoot}/dist/modal` and deploy from there
  - **Fulfills** `WORKER_RESOLVED_MODAL_URL` in the family's `deploy` worker contract, through the executor

**MUST DO before `:deploy-beam`**:

  - **Build** must build `{projectRoot}/dist/modal` and deploy from there
  - **Fulfills** `WORKER_RESOLVED_BEAM_URL` in the family's `deploy` worker contract, through the executor

**MUST DO before `:deploy-flash`**:

  - **Build** must build `{projectRoot}/dist/modal` and deploy from there
  - **Fulfills** `WORKER_RESOLVED_FLASH_URL` in the family's `deploy` worker contract, through the executor

---

## Coding

**Structure**:

- Naming: `worker_{model}_{platform}.py`
- Logic: thin wrapper over provider, logic shared (`apps/{model}|shared/worker_{model}.pu`)
- Types: `Pydantic` generated
- Queue: always use task queue and return task id, except realtime workers

**Worker Config**:

- Max. 1 worker, scale to 0, short idle timeouts, (`workers=(0, 1)`)
- Use `flashboot=True`, `model cache` for quick starts
- Use `Volume` (`./hf-cache`) if provider doesn't do built-in cache
- Models lazy downloaded and cached on first request, `tools/seed-volumes` allowed

**Testing Strategy**

- Rule: value over volume. each test must prove a specced requirement.
- Unit: assert output + artifact for a given input (bad, good), stub side effects
- Working stubs: avoid mocking. rely instead on real stubs + DI to test side effects
- E2E: sole sunny test case per worker asserting output and artifacts, do not stub
