from __future__ import annotations

from types import SimpleNamespace


class FakeImagePipe:
    """Source fake: respond with exactly this image when requested."""

    def __init__(self, image):
        self._image = image

    def __call__(self, **kwargs):
        return SimpleNamespace(images=[self._image])

    def set_adapters(self, adapter_names, weights=None):
        """No-op stub: mirrors the LoRA-adapter hook the real pipe exposes."""
