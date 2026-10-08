"""Tiny image loader: real segmind/tiny-sd inference in production types.

Mirrors FakeImagePipe: pipe(**kwargs) -> namespace with .images[0] as PIL,
plus set_adapters() so Krea2 (LoRA) call sites need no change.
Swap deps to (bucket, load_tiny_image_pipe(), torch); generate() untouched.
"""
from __future__ import annotations

from types import SimpleNamespace

MODEL_ID = "segmind/tiny-sd"
SIZE = 256
STEPS = 4


def load_tiny_image_pipe():
    """Boot the real tiny pipeline. import torch inside function body."""
    import torch
    from diffusers import StableDiffusionPipeline

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    pipe = StableDiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=dtype)
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    return TinyImagePipe(pipe)


class TinyImagePipe:
    """Real pipe with the fake's call shape. Unknown kwargs (image=, ref
    kwargs) are dropped: tiny-sd is text-to-image only, output stays PIL."""

    _KNOWN = ("prompt", "height", "width", "num_inference_steps",
              "guidance_scale", "generator", "num_images_per_prompt")

    def __init__(self, pipe):
        self._pipe = pipe

    def set_adapters(self, adapter_names, weights=None):
        _ = (adapter_names, weights)
        """No-op: tiny-sd carries no LoRA adapters."""

    def __call__(self, **kwargs):
        call_kwargs = {k: kwargs[k] for k in self._KNOWN if k in kwargs}
        call_kwargs.setdefault("height", SIZE)
        call_kwargs.setdefault("width", SIZE)
        call_kwargs.setdefault("num_inference_steps", STEPS)
        call_kwargs.setdefault("guidance_scale", 0.0)
        image = self._pipe(**call_kwargs).images[0].convert("RGB")
        return SimpleNamespace(images=[image])
