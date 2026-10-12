# GPU Workers

**Models**: `flux2`, `krea2`, `tiny_sd`, `vision`, `h3_comfy`, `h3_fl2va`, `h3_ref2va`, `realtime_voice` (`apps/{model}`)

**NX Project**:

- Project `worker-{model}`, e.g. `worker-flux2`
- Targets `dev-modal`, `deploy-modal`
- Each `deploy-*` declares `outputs: [dist/worker-{model}/deploy/deploy-*.env]` plus writes `APP_URL` via `tools/deploy-*`
- Each `dev-*` is `persistent: true`, `cache: false`
- Contract: `packages/contracts/{model}/inference.json`

**Activate**: `modal`, `python-uv`, `cloud-gpu-workers` skills

**Structure**:

- Naming: `worker_{model}_{platform}.py` (`apps/{model}`)
- Contract: has ONLY `input` and `output` (`packages/contracts/{model}/inference.json`)
- Logic: thin wrapper over provider, logic shared (`apps/{model}|shared/worker_{model}.pu`)
- Types: `Pydantic` generated. consumers generate their own types from contract
- Queue: always use task queue and return task id, except realtime workers
- Output: produced files must be delivered as artifact (`packages/artifacts`)

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
