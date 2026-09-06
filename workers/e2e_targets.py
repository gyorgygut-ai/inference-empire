"""E2E rungs: identical run/run_async over in-process fakes or HTTP.

Test-env contract (owner honors at deploy time): POST
{base_url}/{worker_stem} with {"inputs": {...}, "sync": bool}; a sync reply
carries the output contract directly, an async reply carries
{"task_id": ...} polled at GET {base_url}/{task_id} until
{"status": "COMPLETED", "output": ...}.
"""

from __future__ import annotations

import time

from workers.services.runner.runner_fake import FakeAsyncRunner, FakeSyncRunner


class LocalTarget:
    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch

    def run(self, worker_mod, inputs, deps):
        self.monkeypatch.setattr(worker_mod, "load_dependencies", lambda **k: deps)
        return FakeSyncRunner().run(worker_mod, **inputs)

    def run_async(self, worker_mod, inputs, deps):
        self.monkeypatch.setattr(worker_mod, "load_dependencies", lambda **k: deps)
        runner = FakeAsyncRunner()
        return runner.result(runner.submit(worker_mod, **inputs))


class DeployedTarget:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def run(self, worker_mod, inputs, deps):
        return post_and_poll(self.base_url, worker_mod, inputs, sync=True)

    def run_async(self, worker_mod, inputs, deps):
        return post_and_poll(self.base_url, worker_mod, inputs, sync=False)


def post_and_poll(base_url, worker_mod, inputs, sync=True, timeout=1800):
    import requests

    stem = worker_mod.__name__.split(".")[-1]
    resp = requests.post(
        f"{base_url}/{stem}", json={"inputs": inputs, "sync": sync}, timeout=300
    )
    resp.raise_for_status()
    body = resp.json()
    if sync or "task_id" not in body:
        return body
    deadline = time.monotonic() + timeout
    while True:
        poll = requests.get(f"{base_url}/{body['task_id']}", timeout=300)
        poll.raise_for_status()
        state = poll.json()
        if state.get("status") == "COMPLETED":
            return state["output"]
        if state.get("status") in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(f"deployed task {body['task_id']} {state.get('status')}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"deployed task {body['task_id']} timed out")
        time.sleep(1.0)
