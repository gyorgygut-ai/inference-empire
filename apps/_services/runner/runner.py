"""Runner interface: the sync/async vocabulary every provider speaks.

Sync = immediate, same path as async minus latency. Async = task id + poll
loop + 10-500ms latency. Voice fakes use the same interface: the proxy hides
the TestClient websocket exchange behind `generate(**kw)`.
"""

from __future__ import annotations

import secrets
import time
from random import uniform


def check_failure(inputs: dict) -> None:
    """Uniform failure rule: any str kwarg containing "failure" raises."""
    for value in inputs.values():
        if isinstance(value, str) and "failure" in value:
            raise RuntimeError("inference failed: canned failure")


class Runner:
    def run(self, worker, **inputs):
        raise NotImplementedError

    def submit(self, worker, **inputs):
        raise NotImplementedError

    def poll(self, task_id):
        raise NotImplementedError

    def result(self, task_id, timeout=30):
        raise NotImplementedError


class SyncRunner(Runner):
    def run(self, worker, **inputs):
        check_failure(inputs)
        return worker.generate(**inputs)


class AsyncRunner(Runner):
    def __init__(self):
        self._tasks: dict = {}

    def submit(self, worker, **inputs):
        check_failure(inputs)
        task_id = f"task-{secrets.token_hex(4)}"
        self._tasks[task_id] = (worker, inputs, time.monotonic() + uniform(0.01, 0.5))
        return task_id

    def poll(self, task_id):
        _, _, ready_at = self._tasks[task_id]
        return "COMPLETED" if time.monotonic() >= ready_at else "IN_PROGRESS"

    def result(self, task_id, timeout=30):
        deadline = time.monotonic() + timeout
        while self.poll(task_id) != "COMPLETED":
            if time.monotonic() > deadline:
                raise TimeoutError(f"task {task_id} timed out after {timeout}s")
            time.sleep(0.05)
        worker, inputs, _ = self._tasks.pop(task_id)
        return worker.generate(**inputs)

    def run(self, worker, **inputs):
        return self.result(self.submit(worker, **inputs))
