"""Real runners. Owner-operated live path only — never executed in this repo.

Bodies follow the provider mechanics verified against the pinned SDKs:
- Flash (runpod-flash==1.7.0): `await ep.run(payload)` -> EndpointJob;
  `await job.status()` loop -> `job.output` (endpoint.py:744, :113, :99).
- Modal (modal==1.5.5): `generate.spawn(**payload)` -> FunctionCall;
  `await fc.get()` (_functions.py:2035, :2180); class addressed via
  `modal.Cls.from_name(app, cls)` (cls.py:659).
- Beam (beam-client==0.2.207): decorated `wrapper.put(**payload)` -> Task;
  `task.status()` / `is_complete()` / `result()` (beta9/client/task.py:50).
  Task args cross as JSON, so storage is never shipped: remote workers
  build RealR2Storage from env in enter()/generate.

Payload = spec `input_model(**inputs).model_dump()`. `worker` is the
_LiveProxy carrying `_spec`. Flash/Modal SDKs are async: `asyncio.run` +
ThreadPoolExecutor fallback (same trick the comfy flash workers use);
Beam stays sync. Voice serving shapes (beam_asgi/modal_asgi) run over
HTTP/WS against the deployed URL in `live_endpoint`.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import importlib
import secrets
import time


def _payload(worker, inputs):
    model = worker._spec.input_model
    if model is None:
        return dict(inputs)
    return model(**inputs).model_dump()


def _bridge(coro_factory, timeout=1800):
    """Run an async provider call from sync test code (comfy-worker trick)."""
    try:
        return asyncio.run(coro_factory())
    except RuntimeError:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro_factory())).result(timeout)


class _RealRunnerBase:
    def submit(self, worker, **inputs):
        raise NotImplementedError

    def poll(self, task_id):
        raise NotImplementedError

    def result(self, task_id, timeout=30):
        raise NotImplementedError

    def run(self, worker, **inputs):
        raise NotImplementedError


class RealFlashSyncRunner(_RealRunnerBase):
    """Flash `ep.run()` -> `job.id` -> `job.status()` loop -> `job.output`."""

    def run(self, worker, **inputs):
        from runpod_flash import Endpoint

        payload = _payload(worker, inputs)
        endpoint_name = worker._spec.live_endpoint

        async def _run():
            ep = Endpoint(name=endpoint_name)
            job = await ep.run(payload)
            while True:
                status = await job.status()
                if status == "COMPLETED":
                    return job.output
                if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                    raise RuntimeError(f"flash job {job.id} {status}: {job.error}")
                await asyncio.sleep(1.0)

        return _bridge(_run)


class RealFlashAsyncRunner(_RealRunnerBase):
    """Flash `ep.run()` -> `job.id` -> `job.status()` loop -> `job.output`."""

    def __init__(self):
        self._jobs: dict = {}

    def submit(self, worker, **inputs):
        from runpod_flash import Endpoint

        payload = _payload(worker, inputs)

        async def _submit():
            ep = Endpoint(name=worker._spec.live_endpoint)
            return await ep.run(payload)

        task_id = f"task-{secrets.token_hex(4)}"
        self._jobs[task_id] = _bridge(_submit)
        return task_id

    def poll(self, task_id):
        async def _poll():
            return await self._jobs[task_id].status()

        return _bridge(_poll)

    def result(self, task_id, timeout=1800):
        deadline = time.monotonic() + timeout
        while True:
            status = self.poll(task_id)
            if status == "COMPLETED":
                return self._jobs.pop(task_id).output
            if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                job = self._jobs.pop(task_id)
                raise RuntimeError(f"flash job {job.id} {status}: {job.error}")
            if time.monotonic() > deadline:
                raise TimeoutError(f"task {task_id} timed out after {timeout}s")
            time.sleep(1.0)

    def run(self, worker, **inputs):
        return self.result(self.submit(worker, **inputs))


class RealBeamSyncRunner(_RealRunnerBase):
    """Beam endpoint/asgi serving shapes: HTTP/WS against the deployed URL."""

    def run(self, worker, **inputs):
        spec = worker._spec
        if spec.shape in ("beam_asgi", "modal_asgi"):
            return _live_voice_call(spec, inputs)
        import requests

        payload = _payload(worker, inputs)
        resp = requests.post(spec.live_endpoint, json=payload, timeout=1800)
        resp.raise_for_status()
        return resp.json()


class RealBeamAsyncRunner(_RealRunnerBase):
    """Beam `wrapper.put()` -> `Task.id` -> `status()` -> `result()`."""

    def __init__(self):
        self._tasks: dict = {}

    def submit(self, worker, **inputs):
        mod = importlib.import_module(worker._spec.module)
        wrapper = getattr(mod, worker._spec.attr)  # decorated: remote path
        payload = _payload(worker, inputs)
        task = wrapper.put(**payload)
        if task is False:
            raise RuntimeError("beam put() refused the task")
        task_id = f"task-{task.id}"
        self._tasks[task_id] = task
        return task_id

    def poll(self, task_id):
        task = self._tasks[task_id]
        return "COMPLETED" if task.is_complete() else str(task.status())

    def result(self, task_id, timeout=1800):
        return self._tasks.pop(task_id).result(wait=True)

    def run(self, worker, **inputs):
        return self.result(self.submit(worker, **inputs))


class RealModalSyncRunner(_RealRunnerBase):
    """Modal `generate.spawn()` -> `function_call_id` -> `fc.get()`."""

    def run(self, worker, **inputs):
        import modal

        spec = worker._spec
        if spec.shape == "modal_asgi":
            return _live_voice_call(spec, inputs)
        payload = _payload(worker, inputs)

        async def _run():
            cls = modal.Cls.from_name(spec.live_endpoint, spec.attr)
            obj = cls()  # remote enter() builds RealR2Storage from env
            fc = await obj.generate.spawn(**payload)
            return await fc.get()

        return _bridge(_run)


class RealModalAsyncRunner(_RealRunnerBase):
    """Modal `generate.spawn()` -> `function_call_id` -> `fc.get()`."""

    def __init__(self):
        self._calls: dict = {}

    def submit(self, worker, **inputs):
        import modal

        async def _submit():
            cls = modal.Cls.from_name(worker._spec.live_endpoint, worker._spec.attr)
            obj = cls()  # remote enter() builds RealR2Storage from env
            return await obj.generate.spawn(**_payload(worker, inputs))

        task_id = f"task-{secrets.token_hex(4)}"
        self._calls[task_id] = _bridge(_submit)
        return task_id

    def poll(self, task_id):
        return "IN_PROGRESS" if task_id in self._calls else "COMPLETED"

    def result(self, task_id, timeout=1800):
        async def _get():
            return await self._calls[task_id].get()

        try:
            return _bridge(_get, timeout)
        finally:
            self._calls.pop(task_id, None)

    def run(self, worker, **inputs):
        return self.result(self.submit(worker, **inputs))


def _live_voice_call(spec, inputs):
    """Voice live: WS for realtime workers, HTTP for chatterbox TTS.

    `live_endpoint` is the deployed base URL (owner fills it after deploy;
    identity slugs can't address serving endpoints).
    """
    base = spec.live_endpoint
    if spec.extra.get("voice_mode") == "rest":
        import requests

        body = inputs.get("body", {"model": "x", "input": "hello", "voice": "GutAI"})
        path = inputs.get("path", "/v1/audio/speech")
        resp = requests.post(base + path, json=body, timeout=300)
        return {
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type"),
            "content_len": len(resp.content),
        }
    import websocket

    import json

    ws = websocket.create_connection(base + "/v1/realtime", timeout=300)
    try:
        ws.send(json.dumps({k: v for k, v in inputs.items()}))
        return json.loads(ws.recv())
    finally:
        ws.close()
