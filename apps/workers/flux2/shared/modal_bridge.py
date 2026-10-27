import modal
from fastapi import FastAPI, Request

FASTAPI_PIN = "fastapi==0.141.1"

def attach_bridge(app, cls_name, method_name="generate", requires_proxy_auth=True):
    app_name = app.name
    assert app_name is not None
    @app.function(image=modal.Image.debian_slim(python_version="3.11").pip_install(FASTAPI_PIN), serialized=True)
    @modal.asgi_app(label=f"{app_name}-bridge", requires_proxy_auth=requires_proxy_auth)
    def bridge():
        api = FastAPI()
        @api.post("/infer")
        async def infer(request: Request):
            body = await request.json()
            instance = modal.Cls.from_name(app_name, cls_name)()
            call = await getattr(instance, method_name).spawn.aio(**body["input"])
            return {"task_id": call.object_id}
        @api.get("/inquire")
        async def inquire(id: str):
            call = modal.FunctionCall.from_id(id)
            try:
                output = await call.get.aio(timeout=0)
            except TimeoutError:
                return {"status": "processing"}
            except Exception:
                return {"status": "failed"}
            return {"status": "completed", "output": output}
        return api
