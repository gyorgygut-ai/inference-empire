# Worker Authoring

## Critical Specs - Read Before Doing Anything

Read this entire file before working on any worker.

---

## Golden Rules

- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable
- No shortcuts, skimming, fabricating or lying; if task not clear, say it
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

---

## Naming Convention

```
worker_{platform}_{pattern}_{model}.py
```

**Platform:** `flash`, `beam`, `modal`

**Patterns:**

- Flash: `qb` (queue), `lb` (routes), `cls` (class), `pre` (pre-built)
- Beam: `fn` (function), `eq` (endpoint), `tq` (task queue), `asgi`, `pod`
- Modal: `fn` (function), `cls` (class), `fe` (fastapi endpoint), `asgi`

---

## Worker Behaviour

- All workers creating an artifact must upload to R2 and return access to it
- Not all workers produce artifacts; some just return json directly
- Production deps are inline in worker files, not in pyproject.toml

## Contracts

- Contract JSON lives in `contracts/{name}.json` — source of truth
- Every `input` and `output` schema MUST declare a non-empty `required` array
- A field is optional ONLY if it has a `default`
- Update JSON first, then update worker pydantic models to match
- Rules implemented as pydantic validators in the worker, against the JSON

---

## Dependency Constraints

- `transformers` must stay `>=4.57,<5`
- Base flash GPU image has broken torch build — use shim:
  ```python
  import torch.distributed as dist
  dist.is_available = lambda: False
  ```

---

## Flash Rules

**Activate related skills** when working on Runpod Flash.

### Use Flash CLI — Not Runpod REST/GraphQL

| Intent    | Command                  | Do NOT                 |
| --------- | ------------------------ | ---------------------- |
| Local dev | `flash dev`              | Run uvicorn manually   |
| Deploy    | `flash deploy`           | Call REST API directly |
| Preview   | `flash deploy --preview` | Write docker-compose   |
| Tear down | `flash undeploy`         | Call deleteEndpoint    |

Flash is a Python SDK for deploying AI workloads to Runpod GPUs. You write decorated functions, Flash handles infrastructure.

### Patterns

#### Pattern A: Queue-based function (`qb`)

```python
@Endpoint(name="worker", gpu=GpuType.NVIDIA_GEFORCE_RTX_4090, workers=(0, 3), dependencies=["torch"])
async def process(input_data: dict) -> dict:
    import torch
    return {"gpu": torch.cuda.get_device_name(0)}
```

#### Pattern B: Load-balanced routes (`lb`)

```python
api = Endpoint(name="api", cpu="cpu3c-1-2", workers=(1, 3))

@api.get("/health")
async def health():
    return {"status": "ok"}

@api.post("/compute")
async def compute(numbers: list[float]) -> dict:
    return {"sum": sum(numbers)}
```

#### Pattern C: Class-based worker (`cls`)

```python
@Endpoint(name="model", gpu=GpuType.NVIDIA_GEFORCE_RTX_4090, workers=(1, 3), dependencies=["torch", "transformers"])
class MyModel:
    def __init__(self):
        import torch
        self.pipe = pipeline("text-generation", device="cuda")

    async def generate(self, prompt: str) -> dict:
        return {"text": self.pipe(prompt)[0]["generated_text"]}
```

#### Pattern D: Pre-built container (`pre`)

```python
vllm = Endpoint(name="vllm", image="runpod/worker-v1-vllm:v2.18.1", gpu=GpuGroup.ADA_24, workers=(0, 3))
result = await vllm.runsync({"input": {"prompt": "hello"}})
```

### Rules

- `import torch` INSIDE function body, never at module level
- Declare deps in `@Endpoint(dependencies=[...])`, not in pyproject.toml
- `workers=N` is shorthand for `(0, N)`
- Class workers: model loading in `__init__`, request handling in instance methods
- Cross-worker calls use `await`
- System packages (ffmpeg) go in `system_dependencies`
- `flashboot=True` for all stateful workers

---

## Beam Rules

**Activate related skills** when working on Beam.

### Use Beam CLI — Not Beam REST/GraphQL

| Intent    | Command       | Do NOT                 |
| --------- | ------------- | ---------------------- |
| Local dev | `beam serve`  | Run uvicorn manually   |
| Deploy    | `beam deploy` | Call REST API directly |
| Logs      | `beam logs`   | —                      |

Beam is a Python SDK for deploying AI workloads to cloud GPUs. You write decorated functions, Beam handles infrastructure.

### Layout

- One worker per file: `worker_{platform}_{pattern}_{model}.py`
- Each worker is a decorated function with `on_start` for pipeline loading
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`

### Image

```python
from beam import Image

image = (
    Image(python_version="python3.11")  # or python3.10 for ASGI
    .add_python_packages([
        "torch==2.9.1",
        "transformers>=4.57,<5",
        # ... other deps
    ])
    .add_commands(["apt-get update && apt-get install -y ffmpeg"])  # system deps
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)
```

### Volumes

Use `Volume` for caching models across cold starts:

```python
from beam import Volume

CACHE_PATH = "./hf-cache"
volume = Volume(name="hf-cache", mount_path=CACHE_PATH)
```

### Patterns

#### Pattern A: Endpoint (`eq`)

```python
from beam import endpoint, QueueDepthAutoscaler

@endpoint(
    name="worker-name",
    cpu=8,
    memory="64Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
    env={...},
)
def generate(context, prompt: str, ...):
    pipe = context.on_start_value
    # ...
```

#### Pattern B: Task Queue (`tq`)

```python
from beam import task_queue, QueueDepthAutoscaler

@task_queue(
    name="worker-name",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
    env={...},
)
def generate(context, prompt: str, ...) -> dict:
    pipe = context.on_start_value
    # ...
```

#### Pattern C: ASGI (`asgi`)

```python
from beam import asgi, QueueDepthAutoscaler

@asgi(
    name="worker-name",
    image=image,
    volumes=[volume],
    on_start=load_models,
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=4,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    checkpoint_enabled=True,
    secrets=["HF_TOKEN"],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def worker(context):
    models = context.on_start_value
    return build_app(models, ...)
```

### Compute

- GPU: smallest that fits. `RTX4090` (24 GB) default; `RTX5090` for newer models
- `timeout`: 300 s default; -1 for unbounded (ASGI); 3600 s for video
- `memory`: 32-64 Gi depending on model size
- `keep_warm_seconds`: 0 for stateless; 1800 for task queues; 10 for ASGI
- `checkpoint_enabled=True` for task queues to survive container restarts

### Concurrency

- `max_containers=1` for GPU workers
- Do NOT use concurrent execution for model inference — not thread-safe
- Serialize GPU access with `threading.Lock` if needed

### torch load shim

```python
import torch.distributed as dist
dist.is_available = lambda: False
```

### Secrets

Create before deploy: `beam secret create <name> <KEY=value ...>`

---

## Modal Rules

**Activate related skills** when working on Modal.

### Layout

- One worker per file: `worker_{platform}_{pattern}_{model}.py`
- Each worker is a `modal.App` with one `@app.cls` and `@modal.enter()`-loaded pipeline
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`

### Image

- Base: `modal.Image.debian_slim(python_version="3.11")`
- Pin heavy deps; install torch first, then model libs
- Set `HF_HOME=/root/.cache/huggingface` and `HF_HUB_ENABLE_HF_TRANSFER=1`
- Bake models with `.run_function(<download_fn>)` — build runs WITHOUT GPU
- Each worker has its OWN image; do not share across workers

### Compute

- GPU: smallest that fits. `L4` (24 GB) default for multi-model; `T4` (16 GB) only when footprint fits
- `scaledown_window`: 60–150 s for bursty workers
- `max_containers=1` for single-session
- `timeout`: 300 s default; 3600 s for voice/chat
- `memory`: 32768 for LLM-bearing workers

### Concurrency

- Do NOT use `@modal.concurrent` for model inference — not thread-safe
- Serialize GPU access with `threading.Lock`

### torch load shim

```python
import torch.distributed as dist
dist.is_available = lambda: False
```

### Endpoints

- Simple: `@modal.fastapi_endpoint(method="POST")` + `@modal.method()`
- Streaming/WS: `@modal.asgi_app()` returning FastAPI app with WebSocket route

### Secrets

- `modal.Secret.from_name("r2-creds", required_keys=[...])`
- Create before deploy: `modal secret create <name> <KEY=value ...>`

---

## Gotchas

- Flash: `flash dev` bundles ALL `@Endpoint` files in current directory. Each Flash folder is isolated.
- Modal/Beam: target specific files, no per-folder constraint.
- Production deps are inline in worker files. Local venv is for IDE/tests only.
- Testing for status `200` only means the platform fired up the worker.

---

See [Testing Specs](./TESTING.md)
