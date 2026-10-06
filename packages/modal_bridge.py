"""Reusable HTTP bridge in front of any Modal worker.

The worker-router reaches Modal over plain `fetch` because the Modal JS SDK cannot
run in the Cloudflare Workers runtime. `attach_bridge` exposes a worker's class
method through the router's own contract, so `provider-modal.ts` stays a thin proxy:

    POST /infer          {"input": {...}}  -> {"task_id": "fc-..."}
    GET  /inquire?id=...                    -> {"status": "processing"}
                                               {"status": "completed", "output": {...}}
                                               {"status": "failed"}

Attach it with one line at the bottom of a `worker_modal_cls_*.py` file:

    attach_bridge(app, "FluxKleinWorker")
"""

from typing import Any

import modal
from fastapi import FastAPI, Request

# Single source of pins for the bridge image; matches the router-facing contract.
FASTAPI_PIN = "fastapi==0.141.1"


def attach_bridge(
    app: modal.App,
    cls_name: str,
    method_name: str = "generate",
    *,
    requires_proxy_auth: bool = True,
) -> None:
    """Register `cls_name.method_name` on `app` behind a proxy-authenticated web app.

    Web Functions are public by default; `requires_proxy_auth=True` makes Modal
    reject unauthenticated calls at its edge, before a container starts.
    """
    app_name = app.name
    assert app_name is not None

    @app.function(
        image=modal.Image.debian_slim(python_version="3.11").pip_install(FASTAPI_PIN),
        serialized=True,
    )
    @modal.asgi_app(label=f"{app_name}-bridge", requires_proxy_auth=requires_proxy_auth)
    def bridge() -> FastAPI:
        api = FastAPI()

        @api.post("/infer")
        async def infer(request: Request) -> dict[str, Any]:
            body = await request.json()
            instance = modal.Cls.from_name(app_name, cls_name)()
            call = await getattr(instance, method_name).spawn.aio(**body["input"])
            return {"task_id": call.object_id}

        @api.get("/inquire")
        async def inquire(id: str) -> dict[str, Any]:
            call = modal.FunctionCall.from_id(id)
            try:
                output = await call.get.aio(timeout=0)
            except TimeoutError:
                return {"status": "processing"}
            except Exception:
                return {"status": "failed"}
            return {"status": "completed", "output": output}

        return api
