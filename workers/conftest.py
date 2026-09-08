import re
import subprocess
import threading
import time

import modal
import pytest

from workers.services.storage.r2_storage_fake import FakeR2Storage


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


@pytest.fixture(scope="module")
def beam_worker_function_test(request):
    worker_function = request.node.get_closest_marker("beam_worker_function_test").args[0]
    source = open(worker_function.__file__).read()
    match = re.search(r'@(task_queue|endpoint|asgi)\(\s*name="([^"]+)"', source, re.DOTALL)
    assert match is not None
    name = match.group(2)
    t = threading.Thread(target=_stream_beam_logs, args=(name,), daemon=True)
    t.start()
    yield


@pytest.fixture(scope="module")
def modal_worker_function_test(request):
    worker_function = request.node.get_closest_marker("modal_worker_function_test").args[0]
    worker_file = worker_function.__file__
    source = open(worker_file).read()
    match = re.search(r'modal\.App\("([^"]+)"\)', source)
    assert match is not None
    name = match.group(1)
    subprocess.run(["modal", "deploy", worker_file], check=True)
    t = threading.Thread(target=_stream_modal_logs, args=(name,), daemon=True)
    t.start()
    yield
    subprocess.run(["modal", "app", "stop", name, "--yes"], check=False)


@pytest.fixture(scope="module")
def flash_worker_function_test(request):
    worker_function = request.node.get_closest_marker("flash_worker_function_test").args[0]
    source = open(worker_function.__file__).read()
    match = re.search(r'@Endpoint\(\s*name="([^"]+)"', source, re.DOTALL)
    assert match is not None
    name = match.group(2)
    subprocess.run(["flash", "deploy", "--name", name], check=True)
    yield
    subprocess.run(["flash", "undeploy", "--name", name], check=False)


@pytest.fixture
def bucket():
    return FakeR2Storage()
