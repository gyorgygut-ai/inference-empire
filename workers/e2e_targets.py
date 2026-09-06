"""E2E rungs: identical run/run_async over in-process fakes or native provider handles.

Both rungs take (worker_mod, inputs, deps). The local rung patches
`load_dependencies` (proving the seam) then drives module-level `generate`
through the worker's own provider fake (`workers/mock_server/*/fake.py`):
`submit` stashes a zero-arg call, `result` pops and runs it. The call is
`generate(*load_dependencies(), **inputs)` — the loaded tuple passes through
blind; the harness never inspects it. `run`
wraps submit/result; `run_async` additionally exercises the submit/poll loop.
The deployed rung is
built by the module-scoped `deployed_worker` fixture: setup deploys the
worker file, teardown undeploys it. Invokers are provider-native — beam
submits to the task queue and polls the task, modal spawns the class method,
flash calls the endpoint.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from workers.services.runner.runner_local import (
    LocalBeamRunner,
    LocalFlashRunner,
    LocalModalRunner,
)

DEPLOY_TIMEOUT = 1800
TASK_TIMEOUT = 3600

_NAME_PATTERNS = {
    "beam": re.compile(r"@(task_queue|endpoint|asgi)\(\s*name=\"([^\"]+)\"", re.DOTALL),
    "flash": re.compile(r"@Endpoint\(\s*name=\"([^\"]+)\"", re.DOTALL),
    "modal": re.compile(r"modal\.App\(\"([^\"]+)\"\)"),
}
_APP_NAME_REF = re.compile(r"modal\.App\(APP_NAME\)")
_APP_NAME_DEF = re.compile(r"APP_NAME\s*=\s*\"([^\"]+)\"")


_LOCAL_RUNNERS = {
    "flash": LocalFlashRunner,
    "beam": LocalBeamRunner,
    "modal": LocalModalRunner,
}


def local_platform(worker_mod):
    name = getattr(worker_mod, "__name__", "")
    for platform in ("beam", "modal", "flash"):
        if f"worker_{platform}_" in name:
            return platform
    raise ValueError(f"cannot infer provider from {name}")


class LocalTarget:
    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch

    def _call(self, worker_mod, deps, inputs):
        self.monkeypatch.setattr(worker_mod, "load_dependencies", lambda **k: deps)
        loaded = worker_mod.load_dependencies()
        return lambda: worker_mod.generate(*loaded, **inputs)

    def _runner(self, worker_mod):
        return _LOCAL_RUNNERS[local_platform(worker_mod)]()

    def run(self, worker_mod, inputs, deps):
        return self._runner(worker_mod).run(self._call(worker_mod, deps, inputs))

    def run_async(self, worker_mod, inputs, deps):
        runner = self._runner(worker_mod)
        task_id = runner.submit(self._call(worker_mod, deps, inputs))
        deadline = time.monotonic() + 30
        while runner.poll(task_id) != "COMPLETED":
            if time.monotonic() > deadline:
                raise TimeoutError(f"task {task_id} timed out")
            time.sleep(0.01)
        return runner.result(task_id)


def worker_platform(worker_path):
    stem = Path(worker_path).stem
    for platform in ("beam", "modal", "flash"):
        if stem.startswith(f"worker_{platform}_"):
            return platform
    raise ValueError(f"cannot infer provider from {stem}")


def worker_name(worker_path):
    platform = worker_platform(worker_path)
    source = Path(worker_path).read_text()
    match = _NAME_PATTERNS[platform].search(source)
    if match:
        return match.groups()[-1]
    if platform == "modal" and _APP_NAME_REF.search(source):
        definition = _APP_NAME_DEF.search(source)
        if definition:
            return definition.group(1)
    raise LookupError(f"no deploy name literal found in {worker_path}")


def deploy(worker_path):
    """Deploy the worker file; return its deploy name. Fails loud."""
    platform = worker_platform(worker_path)
    path = str(worker_path)
    if platform == "beam":
        cmd, cwd = ["beam", "deploy", path], None
    elif platform == "modal":
        cmd, cwd = ["modal", "deploy", path], None
    else:
        cmd, cwd = ["flash", "deploy"], str(Path(path).parent)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                          timeout=DEPLOY_TIMEOUT, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"deploy failed for {path}:\n{proc.stdout}\n{proc.stderr}")
    return worker_name(worker_path), proc.stdout


def undeploy(worker_path, name):
    """Undeploy the worker file. Fails loud."""
    platform = worker_platform(worker_path)
    if platform == "beam":
        cmd, cwd = ["beam", "worker", "stop", "--name", name], None
    elif platform == "modal":
        cmd, cwd = ["modal", "app", "stop", name], None
    else:
        cmd, cwd = ["flash", "undeploy", "--name", name], str(Path(worker_path).parent)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                          timeout=DEPLOY_TIMEOUT, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"undeploy failed for {name}:\n{proc.stdout}\n{proc.stderr}")


class BeamTarget:
    def __init__(self, stub_id):
        self.stub_id = stub_id

    def _submit(self, inputs):
        from beam import Client
        from beta9.client.deployment import Deployment

        client = Client()
        deployment = Deployment(
            token=client.token,
            base_url=client.base_url,
            workspace_id=client.workspace_id,
            stub_id=self.stub_id,
        )
        return deployment.submit(input=inputs)

    def _resolve(self, out):
        if hasattr(out, "result"):
            return out.result(wait=True)
        return out

    def run(self, worker_mod, inputs, deps, storage):
        return self._resolve(self._submit(inputs))

    def run_async(self, worker_mod, inputs, deps, storage):
        return self._resolve(self._submit(inputs))


class ModalTarget:
    def __init__(self, app_name, cls_name):
        self.app_name = app_name
        self.cls_name = cls_name

    def _method(self):
        import modal

        return modal.Cls.from_name(self.app_name, self.cls_name).generate

    def run(self, worker_mod, inputs, deps, storage):
        return self._method().remote(**inputs)

    def run_async(self, worker_mod, inputs, deps, storage):
        return self._method().spawn(**inputs).get()


class FlashTarget:
    def __init__(self, endpoint_id):
        import runpod

        self.endpoint = runpod.Endpoint(endpoint_id)

    def run(self, worker_mod, inputs, deps, storage):
        return self.endpoint.run_sync(inputs)

    def run_async(self, worker_mod, inputs, deps, storage):
        job = self.endpoint.run(inputs)
        deadline = time.monotonic() + TASK_TIMEOUT
        while True:
            status = job.status()
            if status == "COMPLETED":
                return job.output()
            if status in ("FAILED", "TIMED_OUT", "CANCELLED"):
                raise RuntimeError(f"flash job {status}: {job.output()}")
            if time.monotonic() > deadline:
                raise TimeoutError("flash job timed out")
            time.sleep(5.0)


def modal_cls_name(worker_mod):
    for name, obj in vars(worker_mod).items():
        if type(obj).__name__ == "Cls":
            return name
    raise LookupError(f"no modal Cls found in {worker_mod.__name__}")


def flash_endpoint_id(name):
    import runpod

    for ep in runpod.get_endpoints():
        ep_name = ep.get("name") if isinstance(ep, dict) else getattr(ep, "name", None)
        if ep_name == name:
            return ep.get("id") if isinstance(ep, dict) else ep.id
    raise LookupError(f"flash endpoint {name!r} not found after deploy")


def parse_beam_stub(deploy_output):
    match = re.search(r"stub[_-]?id[:\s=]+([A-Za-z0-9_-]+)", deploy_output,
                      re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"https://\S+", deploy_output)
    if match:
        return match.group(0)
    raise LookupError(f"no stub id or URL in beam deploy output:\n{deploy_output}")


def make_deployed_target(worker_mod, worker_path, deploy_output):
    platform = worker_platform(worker_path)
    name = worker_name(worker_path)
    if platform == "beam":
        return BeamTarget(parse_beam_stub(deploy_output))
    if platform == "modal":
        return ModalTarget(worker_mod.app.name, modal_cls_name(worker_mod))
    return FlashTarget(flash_endpoint_id(name))


class DeployedRunner:
    """Lazy native invoker; deploy happens in fixture setup, handle resolves
    on first call (modal needs the imported module)."""

    def __init__(self, worker_path, deploy_output):
        self.worker_path = worker_path
        self.deploy_output = deploy_output
        self._target = None

    def _target_for(self, worker_mod):
        if self._target is None:
            self._target = make_deployed_target(
                worker_mod, self.worker_path, self.deploy_output)
        return self._target

    def run(self, worker_mod, inputs, deps, storage=None):
        return self._target_for(worker_mod).run(worker_mod, inputs, deps, storage)

    def run_async(self, worker_mod, inputs, deps, storage=None):
        return self._target_for(worker_mod).run_async(
            worker_mod, inputs, deps, storage)
