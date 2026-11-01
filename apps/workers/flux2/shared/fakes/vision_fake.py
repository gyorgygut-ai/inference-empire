from __future__ import annotations

import json


class FakeVisionModel:
    """Source fake: generate returns one row; the processor decodes it."""

    def __init__(self, result: dict):
        self._result = result

    def generate(self, **kwargs):
        return [[None]]


class FakeVisionProcessor:
    """Source fake: canned result dict in, JSON text out of decode."""

    def __init__(self, result: dict):
        self._result = result

    def apply_chat_template(self, messages, **kwargs):
        return "fake-prompt"

    def __call__(self, **kwargs):
        return _FakeInputs()

    def decode(self, generated, **kwargs):
        return json.dumps(self._result)


class _FakeInputs(dict):
    def __init__(self):
        super().__init__(input_ids=_FakeTensor())

    @property
    def input_ids(self):
        return self["input_ids"]

    def to(self, device):
        return self


class _FakeTensor:
    shape = (1, 0)

    def __getitem__(self, key):
        return []
