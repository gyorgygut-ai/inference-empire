# GPU Workers

**Models**: `flux2`, `krea2`, `tiny_sd`, `vision`, `h3_comfy`, `h3_fl2va`, `h3_ref2va`, `realtime_voice` (`apps/{model}`)
**Schema**: `packages/schemas/{model}/schema.json`

---

## NX Targets

**worker-{model}:dev-modal|dev-beam|dev-flash**:

- **executor**: `orchestrator/run-command`
- **command**: `tools/serve-{modal|beam|flash}.ts`
- **envKey**: `{MODAL|BEAM|FLASH}_WORKER_URL`
- **critical**: command must output served dev url to stdout
- **outcome**: the executor writes the output to `envFile`

**worker-{model}:deploy-modal|deploy-beam|deploy-flash**:

- **executor**: `orchestrator/run-command`
- **command**: `tools/deploy-{modal|beam|flash}.ts`
- **envKey**: `{MODAL|BEAM|FLASH}_WORKER_URL`
- **critical**: command must output deployed url to stdout
- **outcome**: the executor writes the output to `envFile`

---

## Coding

**Structure**:

- Naming: `worker_{model}_{platform}.py` (`apps/{model}`)
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
