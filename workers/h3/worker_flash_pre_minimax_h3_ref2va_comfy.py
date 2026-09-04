from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup, PodTemplate

from workers.h3.generate_minimax_h3_ref2va_comfy import (
    ValidatedRef2VAComfyInput,
    build_payload,
    parse_output,
    upload_result,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


@Endpoint(
    name="minimax-h3-ref2va-comfy-worker",
    gpu=[GpuGroup.ADA_32_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    execution_timeout_ms=3600_000,
    template=PodTemplate(containerDiskInGb=150),
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
)
class MiniMaxH3Ref2VAComfyWorker:
    Input = ValidatedRef2VAComfyInput

    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

        import torch.distributed as dist

        dist.is_available = lambda: False
        from runpod_flash import Endpoint

        self.endpoint = Endpoint(
            name="minimax-h3-ref2va-comfy-backend",
            image="ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
            gpu=[GpuGroup.ADA_32_PRO],
        )

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, submit to ComfyUI backend, return output contract."""
        req = self.Input(**kwargs)
        payload = build_payload(req)

        import asyncio

        async def _run():
            return await self.endpoint.runsync(payload, timeout=1800)

        try:
            job = asyncio.run(_run())
        except RuntimeError:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                job = pool.submit(lambda: asyncio.run(_run())).result()

        if getattr(job, "error", None):
            raise RuntimeError(f"job failed: {job.error}")

        output = getattr(job, "output", None) or job
        video_bytes, data = parse_output(output)

        return upload_result(self.storage, video_bytes, data).model_dump()
