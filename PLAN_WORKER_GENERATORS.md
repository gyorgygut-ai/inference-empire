# Worker Generators — Full Plan

> Pending: final name for the ASGI workload generator (`<TBD>` below).
> Candidates: app, server, web, socket, daemon.

## Goal

Replace hand-maintained per-provider wrappers with three workload generators.
Each generator emits all three providers plus tests in one run.
Generated files are checked in. CI fails on stale output.

## Workload types

- `queue`: async job queue with polling. Submit a job, poll for the result.
  One-shot inference, scale-to-0. Workers: flux2, krea2, tiny_sd, vision,
  h3_fl2va, h3_ref2va.
- `<TBD>`: regular web endpoint. Resident app serving requests over HTTP.
  Worker: realtime_voice.
- `comfyui`: inference delegated to a bundled engine process over localhost.
  Worker: h3_comfy.

## Sources

- `apps/<name>/contract_<name>.json`: sole type truth for input plus output.
  Feeds schema `input`/`output`.
- `apps/<name>/<name>.py`: pure logic plus model constants. Zero provider
  imports. Exports `Input`, `load_dependencies`, `do_inference` by convention.
  Constants feed schema `vars`.
- `apps/<name>/requirements.lock`: frozen transitive closure with hashes,
  produced by `uv export --frozen`. Feeds schema `dependencies`. Shipped
  artifact consumed by all providers. (queue and `<TBD>` types only;
  comfyui uses a pinned registry image instead.)
- Nx target options: GPU SKU, CPU, memory per provider, plus model env
  extras. Feeds schema `env`/`compute`. Numbers live in Nx.
- Generation input is the assembled document (contract plus vars plus deps
  plus options), validated against the workload schema before emit.

## Schemas

One per workload. No `kind` field (`$id` discriminates). Only per-worker
fields; everything template-derivable is excluded.

### queue

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://inference-empire/worker-queue.schema.json",
  "title": "worker-queue",
  "type": "object",
  "required": ["name", "input", "output", "vars", "dependencies", "compute"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "input": { "$ref": "#/$defs/jsonSchema" },
    "output": { "$ref": "#/$defs/jsonSchema" },
    "vars": { "type": "object", "minProperties": 1 },
    "dependencies": { "type": "array", "minItems": 1, "items": { "type": "string" } },
    "env": { "type": "object", "additionalProperties": { "type": "string" } },
    "compute": {
      "type": "object",
      "required": ["modal", "beam", "flash"],
      "additionalProperties": false,
      "properties": {
        "modal": {
          "type": "object", "required": ["gpu", "memoryMb"], "additionalProperties": false,
          "properties": { "gpu": { "type": "string" }, "memoryMb": { "type": "integer" } }
        },
        "beam": {
          "type": "object", "required": ["gpu", "cpu", "memory"], "additionalProperties": false,
          "properties": {
            "gpu": { "type": "string" },
            "cpu": { "type": "integer" },
            "memory": { "type": "string", "pattern": "^[0-9]+Gi$" }
          }
        },
        "flash": {
          "type": "object", "required": ["gpuGroups"], "additionalProperties": false,
          "properties": { "gpuGroups": { "type": "array", "minItems": 1, "items": { "type": "string" } } }
        }
      }
    }
  },
  "$defs": {
    "jsonSchema": {
      "type": "object", "required": ["title", "properties"],
      "properties": {
        "title": { "type": "string" },
        "required": { "type": "array", "items": { "type": "string" } },
        "properties": { "type": "object" }
      }
    }
  }
}
<TBD> (realtime_voice shape; name pending)
Same as queue, plus noDeps for the --no-deps layer (e.g.
CHATTERBOX_TTS). CUDA base image, persistent serving, build_app /
handle_webrtc_audio wiring, concurrent_requests, and extended timeouts
stay hardcoded in this generator's template.
comfyui
Same envelope, but dependencies is replaced by baseImage (pinned
registry digest) plus optional comfyModels. additionalProperties: false
rejects dependencies. Sidecar start, port, and comfy_base_url wiring
stay hardcoded in this generator's template.
Flux2 instance against the queue schema
{
  "name": "flux2-klein9b",
  "input": { "title": "Flux2Klein9bInput", "properties": { "prompt": { "type": "string" } } },
  "output": { "title": "Flux2Klein9bOutput", "properties": { "artifact": { "type": "object" } } },
  "vars": { "MODEL_ID": "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32", "_MAX_WIDTH": 2560, "_MAX_HEIGHT": 2560 },
  "dependencies": ["torch==2.9.1", "diffusers==0.40.0", "sdnq==0.2.6"],
  "env": { "SDNQ_USE_TRITON_MM": "0" },
  "compute": {
    "modal": { "gpu": "L4", "memoryMb": 32768 },
    "beam": { "gpu": "RTX4090", "cpu": 4, "memory": "32Gi" },
    "flash": { "gpuGroups": ["AMPERE_16"] }
  }
}
Generators
- worker-generator-queue
- Inputs: contract path, worker path, lock path, output path, plus
target options.
- Emits in one run: modal worker plus beam worker plus flash worker
plus unit tests plus e2e tests.
- Template owns: @app.cls / @task_queue / @Endpoint, @modal.enter
vs on_start vs __init__, context.on_start_value unpack, image
bases, python_version, apt list, handler skeleton
(generate() via run_guarded), import wiring, {name}-worker names,
secrets pattern, scaling numbers, timeouts.
- worker-generator-<TBD>
- Same run shape. Template owns the app-serving variant (asgi_app /
@asgi / Endpoint with webrtc handler), CUDA base, noDeps install
layer, persistent scaling.
- worker-generator-comfyui
- Same run shape. Template owns registry base, sidecar start, model
ensure, comfy_base_url wiring.
- Shared helper: spec assembly plus schema validation plus naming
conventions. Templates stay separate. Output directory derives from
worker path.
Targets Per Worker
- generate-worker-<type>: run-commands invoking the matching generator
in write mode.
- build-<type>: same generator in check mode. Fails on diff.
- build: depends on the check target.
- Inference plugin detects the spec bundle (<name>.py plus
contract_<name>.json plus requirements.lock) and infers both targets
with paths prefilled.
Dependency Uniformity
- Intent lives in pyproject. Truth lives in uv.lock. Shipped artifact
is requirements.lock.
- Modal consumes the lock path through pip_install_from_requirements.
Beam consumes the lock path through python_packages. Flash consumes lock
file lines as the dependencies list.
- Lint forbids == pins inside worker_*.py. validate-deps compiles the
lock for the declared Python version.
- Image cache busts on lock hash. Base images pinned by digest. Python micro
versions pinned per worker.
Phases
Phase 1: queue generator plus flux2 pilot
1. Add shared helper for spec assembly plus schema validation.
2. Add worker-generator-queue with all three provider templates plus
tests templates.
3. Point it at packages/contracts/flux2/contract.json plus apps/flux2/flux2.py
plus apps/flux2/requirements.lock.
4. Generate flux2 workers plus tests. Commit outputs.
5. Wire targets for flux2. Update inference plugin glob.
Phase 2: remaining generators
1. Add worker-generator-<TBD> with app-serving plus webrtc variants.
2. Add worker-generator-comfyui with sidecar variant.
3. Generate realtime_voice plus h3_comfy. Commit outputs.
Phase 3: Rollout plus enforcement
1. Generate remaining queue workers: krea2, tiny_sd, vision, h3_fl2va,
h3_ref2va.
2. Delete hand-written wrappers replaced by outputs.
3. Remove the gpu-family scaffolding. Keep it as thin composer calling
the three generators.
4. Migrate executors off worker-group inputs to path inputs.
5. Enable check mode in CI for every build-* target.
Verification
1. nx run flux2:generate-worker-queue writes all three workers plus
tests with zero manual edits.
2. Rerun in check mode passes clean on committed tree.
3. nx run flux2:build passes the check target.
4. nx run flux2:lint passes ruff plus ty plus vulture with generated
files present.
5. nx run flux2:test-unit passes generated unit tests.
6. nx run flux2:test-e2e -k e2e passes sunny path asserting output plus
artifacts.
7. nx run-many -t build passes empire-wide with no stale outputs.
8. H3 workers show zero inline pin lists. Lock file is the single
dependency source.

Two things I resolved while drafting — flag if you disagree:

- Compute/env live in Nx target options and get assembled into the validated spec (keeps "numbers live in Nx", schemas stay file-format-free).
- Each worker needs only its own type's two targets, not all six (a worker is exactly one workload).
```
