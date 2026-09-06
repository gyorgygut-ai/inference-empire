"""Local runners: thin submit/poll/result/run over each provider's own fake dict."""

from __future__ import annotations

from workers.mock_server.beam import fake as beam_fake
from workers.mock_server.flash import fake as flash_fake
from workers.mock_server.modal import fake as modal_fake


class LocalFlashRunner:
    def submit(self, call):
        return flash_fake.submit(call)

    def poll(self, task_id):
        return flash_fake.poll(task_id)

    def result(self, task_id, timeout=30):
        return flash_fake.result(task_id)

    def run(self, call):
        return self.result(self.submit(call))


class LocalBeamRunner:
    def submit(self, call):
        return beam_fake.submit(call)

    def poll(self, task_id):
        return beam_fake.poll(task_id)

    def result(self, task_id, timeout=30):
        return beam_fake.result(task_id)

    def run(self, call):
        return self.result(self.submit(call))


class LocalModalRunner:
    def submit(self, call):
        return modal_fake.submit(call)

    def poll(self, task_id):
        return modal_fake.poll(task_id)

    def result(self, task_id, timeout=30):
        return modal_fake.result(task_id)

    def run(self, call):
        return self.result(self.submit(call))
