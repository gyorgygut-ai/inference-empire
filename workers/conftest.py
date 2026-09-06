import subprocess
import threading

import modal
import pytest


def _stream_modal_logs(app_name):
    app = modal.App.lookup(app_name)
    for entry in app.logs.stream(timeout=None):
        print(entry.message, end="", flush=True)


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
    from workers.flux2.worker_beam_tq_flux2_klein9b import dispatch

    print("[beam] setup: deploying ...", flush=True)
    subprocess.run(
        ["beam", "deploy", "workers/flux2/worker_beam_tq_flux2_klein9b.py"],
        check=True,
    )
    print("[beam] setup: yielding dispatch", flush=True)
    print("[beam] note: beam logs has no follow/stream mode", flush=True)
    yield dispatch
    print("[beam] teardown: beam worker stop --name flux2-klein9b-worker", flush=True)
    subprocess.run(
        ["beam", "worker", "stop", "--name", "flux2-klein9b-worker"],
        check=False,
    )


@pytest.fixture(scope="module")
def platform_modal():
    print("[modal] setup: deploying ...", flush=True)
    subprocess.run(
        ["modal", "deploy", "workers/flux2/worker_modal_cls_flux2_klein9b.py"],
        check=True,
    )
    print("[modal] setup: starting log stream ...", flush=True)
    t = threading.Thread(
        target=_stream_modal_logs,
        args=("flux2-klein9b-worker",),
        daemon=True,
    )
    t.start()
    yield
    print("[modal] teardown: stopping app ...", flush=True)
    subprocess.run(
        ["modal", "app", "stop", "flux2-klein9b-worker", "--yes"],
        check=False,
    )


@pytest.fixture(scope="module")
def bucket():
    from workers.services.storage.r2_storage_fake import FakeR2Storage

    return FakeR2Storage()
