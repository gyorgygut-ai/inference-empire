"""Universal fakes for local tests. Imported by every group's conftest.py."""
import base64
import io
import random
import time


class FakeR2:
    """In-memory R2 storage. put_object saves to dict, generate_presigned_url returns fake URL."""

    def __init__(self):
        self.buckets = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        if Bucket not in self.buckets:
            self.buckets[Bucket] = {}
        self.buckets[Bucket][Key] = Body

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        key = Params["Key"]
        return f"https://fake.r2.cloudflarestorage.com/{key}?X-Amz-Signature=fake"


class FakeTorch:
    """Minimal torch mock for inference."""

    class Generator:
        def __init__(self, device=None):
            self.device = device

        def manual_seed(self, seed):
            return self

    torch = None  # set to FakeTorch on workers that use self.torch


class FakeFailingPipeline:
    """Pipeline that always raises."""

    def __init__(self):
        self.torch = FakeTorch

    def to(self, device):
        return self

    def __call__(self, **kw):
        raise RuntimeError("inference failed")


def fake_png(width=512, height=512, color="red"):
    """Return bytes of a fake PNG image."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


class FakeTaskQueue:
    """In-memory task queue. submit() returns task_id immediately. await resolves after 10-300ms."""

    def __init__(self, fn):
        self._fn = fn
        self._tasks = {}

    def submit(self, **kwargs):
        task_id = f"task-{len(self._tasks):06d}"
        self._tasks[task_id] = {"id": task_id, "fn": self._fn, "kwargs": kwargs, "resolved": False}
        return task_id

    def _resolve(self, task_id):
        if task_id in self._tasks and not self._tasks[task_id]["resolved"]:
            self._tasks[task_id]["resolved"] = True
            self._tasks[task_id]["result"] = self._tasks[task_id]["fn"](**self._tasks[task_id]["kwargs"])

    def poll(self, task_id):
        self._resolve(task_id)
        task = self._tasks.get(task_id)
        if task and task["resolved"]:
            return task["result"]
        return None

    async def wait(self, task_id, timeout=30):
        import asyncio

        deadline = time.time() + timeout
        while time.time() < deadline:
            self._resolve(task_id)
            task = self._tasks.get(task_id)
            if task and task["resolved"]:
                return task["result"]
            await asyncio.sleep(random.uniform(0.01, 0.3))
        raise TimeoutError(f"task {task_id} did not resolve in {timeout}s")


def fake_asgi_context(payload):
    """Build an ASGI scope dict for Beam asgi workers."""
    return {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
        "json": lambda: payload,
    }