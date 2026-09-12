"""Local runners: HTTP calls to each platform's mock server for queue simulation."""
from __future__ import annotations

import requests

FLASH_URL = "http://127.0.0.1:9000"
BEAM_URL = "http://127.0.0.1:9001"
MODAL_URL = "http://127.0.0.1:9002"


class LocalFlashRunner:
    def submit(self, call):
        resp = requests.post(f"{FLASH_URL}/run", json={"input": {}}, timeout=5)
        resp.raise_for_status()
        return resp.json()["id"]

    def poll(self, task_id):
        resp = requests.get(f"{FLASH_URL}/status/{task_id}", timeout=5)
        resp.raise_for_status()
        return resp.json().get("status", "UNKNOWN")

    def complete(self, task_id, output):
        requests.post(f"{FLASH_URL}/status/{task_id}/complete", json=output, timeout=5)

    def run(self, call):
        task_id = self.submit(call)
        result = call()
        self.complete(task_id, result)
        return result


class LocalBeamRunner:
    def submit(self, call):
        resp = requests.post(f"{BEAM_URL}/v1/tasks", json={"input": {}}, timeout=5)
        resp.raise_for_status()
        return resp.json()["task_id"]

    def poll(self, task_id):
        resp = requests.get(f"{BEAM_URL}/v1/tasks/{task_id}", timeout=5)
        resp.raise_for_status()
        return resp.json().get("status", "UNKNOWN")

    def complete(self, task_id, output):
        requests.post(f"{BEAM_URL}/v1/tasks/{task_id}/complete", json=output, timeout=5)

    def run(self, call):
        task_id = self.submit(call)
        result = call()
        self.complete(task_id, result)
        return result


class LocalModalRunner:
    def submit(self, call):
        resp = requests.post(f"{MODAL_URL}/v1/calls", json={"input": {}}, timeout=5)
        resp.raise_for_status()
        return resp.json()["call_id"]

    def poll(self, task_id):
        resp = requests.get(f"{MODAL_URL}/v1/calls/{task_id}", timeout=5)
        resp.raise_for_status()
        return resp.json().get("status", "UNKNOWN")

    def complete(self, task_id, output):
        requests.post(f"{MODAL_URL}/v1/calls/{task_id}/complete", json=output, timeout=5)

    def run(self, call):
        task_id = self.submit(call)
        result = call()
        self.complete(task_id, result)
        return result
