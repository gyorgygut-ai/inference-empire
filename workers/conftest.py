import inspect
import re
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import modal
import pytest


def _stream_modal_logs(app_name):
    app = modal.App.lookup(app_name)
    for entry in app.logs.stream(timeout=None):
        print(entry.message, end="", flush=True)


def _stream_beam_logs(stub_id):
    while True:
        proc = subprocess.run(
            ["beam", "logs", "--stub-id", stub_id],
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            print(proc.stdout, end="", flush=True)
        time.sleep(5)


# =============================================================================
# NEW: Worker function test fixtures
# =============================================================================


@pytest.fixture
def beam_worker_function_test(request):
    t = threading.Thread(target=_stream_beam_logs, args=("flux2-klein9b-worker",), daemon=True)
    t.start()
    yield


@pytest.fixture
def modal_worker_function_test(request):
    marker = request.node.get_closest_marker("modal_worker_function_test")
    worker_function = marker.args[0]

    subprocess.run(
        ["modal", "deploy", "workers/flux2/worker_modal_cls_flux2_klein9b.py"], check=True
    )

    t = threading.Thread(target=_stream_modal_logs, args=("flux2-klein9b-worker",), daemon=True)
    t.start()

    yield

    subprocess.run(["modal", "app", "stop", "flux2-klein9b-worker", "--yes"], check=False)


@pytest.fixture
def flash_worker_function_test(request):
    marker = request.node.get_closest_marker("flash_worker_function_test")
    worker_function = marker.args[0]

    subprocess.run(["flash", "deploy", "--name", "flux2-klein9b-worker"], check=True)

    yield

    subprocess.run(["flash", "undeploy", "--name", "flux2-klein9b-worker"], check=False)


# =============================================================================
# This is shit: drop
# =============================================================================


def _get_test_module_path() -> Path:
    frame = inspect.currentframe()
    try:
        while frame:
            module = inspect.getmodule(frame)
            if module:
                mod_name = getattr(module, "__name__", "")
                mod_file = getattr(module, "__file__", "")
                if mod_name.startswith("workers.") and ".tests." in mod_name and mod_file:
                    return Path(mod_file)
            frame = frame.f_back
    finally:
        del frame
    raise RuntimeError("could not find calling test module")


def _worker_path_from_test(test_path: Path) -> Path:
    return test_path.parent.parent / test_path.name.replace("test_e2e_worker_", "worker_")


def _worker_name(worker_path: Path) -> str:
    source = worker_path.read_text()
    platform = None
    for p in ("beam", "modal", "flash"):
        if worker_path.name.startswith(f"worker_{p}_"):
            platform = p
            break
    if platform == "beam":
        match = re.search(r'@(task_queue|endpoint|asgi)\(\s*name="([^"]+)"', source, re.DOTALL)
        if match:
            return match.group(2)
    elif platform == "modal":
        match = re.search(r'modal\.App\("([^"]+)"\)', source)
        if match:
            return match.group(1)
        match = re.search(r'APP_NAME\s*=\s*"([^"]+)"', source)
        if match:
            return match.group(1)
    elif platform == "flash":
        match = re.search(r'@Endpoint\(\s*name="([^"]+)"', source, re.DOTALL)
        if match:
            return match.group(1)
    raise LookupError(f"no deploy name literal found in {worker_path}")


@pytest.fixture(scope="module")
def platform_flash():
    from workers.flux2.worker_flash_cls_flux2_klein9b import FluxKleinWorker

    print("[flash] setup: yielding FluxKleinWorker", flush=True)
    print("[flash] note: no CLI log streaming available for Flash endpoints", flush=True)
    yield FluxKleinWorker
    print("[flash] teardown: flash undeploy --name flux2-klein9b-worker", flush=True)
    subprocess.run(
        ["flash", "undeploy", "--name", "flux2-klein9b-worker"],
        check=False,
    )


@pytest.fixture(scope="module")
def platform_beam():
    test_path = _get_test_module_path()
    worker_path = _worker_path_from_test(test_path)
    name = _worker_name(worker_path)
    worker_mod = __import__(
        f"workers.{worker_path.relative_to('workers').parent.name}.{worker_path.stem}",
        fromlist=["dispatch"],
    )

    print(f"[beam] setup: yielding dispatch from {worker_path.name}", flush=True)
    print(f"[beam] setup: streaming logs for stub '{name}' ...", flush=True)
    t = threading.Thread(
        target=_stream_beam_logs,
        args=(name,),
        daemon=True,
    )
    t.start()
    yield worker_mod.dispatch
    print(f"[beam] teardown: beam worker stop --name {name}", flush=True)
    subprocess.run(
        ["beam", "worker", "stop", "--name", name],
        check=False,
    )


@pytest.fixture(scope="module")
def platform_modal():
    test_path = _get_test_module_path()
    worker_path = _worker_path_from_test(test_path)
    name = _worker_name(worker_path)

    print(f"[modal] setup: deploying {worker_path.name} ...", flush=True)
    subprocess.run(
        ["modal", "deploy", str(worker_path)],
        check=True,
    )
    print(f"[modal] setup: streaming logs for app '{name}' ...", flush=True)
    t = threading.Thread(
        target=_stream_modal_logs,
        args=(name,),
        daemon=True,
    )
    t.start()
    yield
    print(f"[modal] teardown: stopping app '{name}' ...", flush=True)
    subprocess.run(
        ["modal", "app", "stop", name, "--yes"],
        check=False,
    )


@pytest.fixture(scope="module")
def bucket():
    from workers.services.storage.r2_storage_fake import FakeR2Storage

    return FakeR2Storage()
