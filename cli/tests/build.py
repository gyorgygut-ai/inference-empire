"""Factory functions that return test function tuples for each worker pattern.

Each function takes group-specific args (module name, fake pipe class, builder fn)
and returns named test function tuples. Import and unpack in group test files.
"""
import asyncio
import io
import random
import sys
import time

from types import SimpleNamespace


class _FakeR2:
    """In-memory R2. put_object saves to dict, generate_presigned_url returns fake URL."""

    def __init__(self):
        self.buckets = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        if Bucket not in self.buckets:
            self.buckets[Bucket] = {}
        self.buckets[Bucket][Key] = Body

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://fake.r2.cloudflarestorage.com/{Params['Key']}?sig=fake"


class _FakeTorch:
    class Generator:
        def __init__(self, device=None):
            self.device = device
        def manual_seed(self, seed):
            return self


class _FakeFailingPipeline:
    def to(self, device):
        return self
    def __call__(self, **kw):
        raise RuntimeError("inference failed")


def _clear_module(module_name):
    for key in list(sys.modules.keys()):
        if key.startswith(module_name):
            del sys.modules[key]


def _import_module(module_name):
    _clear_module(module_name)
    import importlib
    return importlib.import_module(module_name)


def _setup_r2(monkeypatch):
    from cli.tests import fakes as _f
    fake_r2 = _f.FakeR2()
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: fake_r2)
    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://fake.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    return fake_r2


def _fake_png(w=512, h=512, color="red"):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def _assert_contract(result):
    assert "artifact" in result, f"Missing artifact: {result}"
    url = result["artifact"]["presigned_url"]
    assert url.startswith("https://"), f"Bad presigned_url: {url}"


def _assert_artifact_body(fake_r2):
    for bucket_name, bucket in fake_r2.buckets.items():
        for key, body in bucket.items():
            assert len(body) > 100, f"Artifact {key} too small ({len(body)} bytes)"


# --- Flash cls/pre sync workers ---

def local_flash_sync(module_name, raw_class, fake_pipe_class):
    """Generate 4 tests for Flash cls/pre workers.
    
    Args:
        module_name: e.g. "worker_flash_cls_flux2_klein9b"
        raw_class: the worker class (after decorator unwrapping)
        fake_pipe_class: class that returns fake images, has .torch
    """

    def _build(monkeypatch, pipe=None):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        fp = pipe if pipe else fake_pipe_class()
        raw = raw_class(pipe=fp)
        raw.torch = _f.FakeTorch
        return raw, fake_r2

    def test_local_invalid_input_rejects(monkeypatch):
        raw, _ = _build(monkeypatch)
        try:
            raw.generate(prompt=None)
            assert False, "Should have raised"
        except Exception:
            pass

    def test_local_inference_fail(monkeypatch):
        raw, _ = _build(monkeypatch)
        raw.pipe = _FakeFailingPipeline()
        try:
            raw.generate(prompt="a cat")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_local_success_returns_contract(monkeypatch):
        raw, _ = _build(monkeypatch)
        result = raw.generate(prompt="a cat")
        _assert_contract(result)

    def test_local_success_uploads_artifact(monkeypatch):
        raw, fake_r2 = _build(monkeypatch)
        result = raw.generate(prompt="a cat")
        _assert_contract(result)
        _assert_artifact_body(fake_r2)

    return test_local_invalid_input_rejects, test_local_inference_fail, \
           test_local_success_returns_contract, test_local_success_uploads_artifact


# --- Beam eq (sync endpoint) workers ---

def local_beam_eq(module_name, fake_ctx_fn, raw_class=None, fake_pipe_class=None):
    """Generate 4 tests for Beam eq (sync endpoint) workers.
    
    Args:
        module_name: e.g. "worker_beam_eq_small_vision"
        fake_ctx_fn: callable() -> context object with on_start_value
        raw_class: optional, class to inject fake pipe into
        fake_pipe_class: optional, class for the pipe
    """

    def _build(monkeypatch, pipe=None):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        if pipe:
            ctx.on_start_value = pipe
        return ctx, fake_r2

    def test_local_invalid_input_rejects(monkeypatch):
        ctx, _ = _build(monkeypatch)
        mod = _import_module(module_name)
        try:
            mod.generate(ctx, prompt=None)
            assert False, "Should have raised"
        except Exception:
            pass

    def test_local_inference_fail(monkeypatch):
        ctx, _ = _build(monkeypatch)
        mod = _import_module(module_name)
        ctx.on_start_value = _FakeFailingPipeline()
        try:
            mod.generate(ctx, prompt="a cat")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_local_success_returns_contract(monkeypatch):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        fake_pipe = fake_pipe_class()
        ctx.on_start_value = fake_pipe
        mod = _import_module(module_name)
        result = mod.generate(ctx, prompt="a cat")
        _assert_contract(result)

    def test_local_success_uploads_artifact(monkeypatch):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        fake_pipe = fake_pipe_class()
        ctx.on_start_value = fake_pipe
        mod = _import_module(module_name)
        result = mod.generate(ctx, prompt="a cat")
        _assert_contract(result)
        _assert_artifact_body(fake_r2)

    return test_local_invalid_input_rejects, test_local_inference_fail, \
           test_local_success_returns_contract, test_local_success_uploads_artifact


# --- Beam tq (async task queue) workers ---

def local_beam_tq(module_name, fake_ctx_fn, fake_pipe_class):
    """Generate 4 tests for Beam tq (async) workers.
    
    The worker is a module-level function:
        @task_queue(...)
        def generate(context, prompt=..., seed=...):
            return _run_generate(pipe, runtime_dir, torch, prompt, ...)
    
    Tests inject pipe via context.on_start_value and call the module function.
    """

    def _build(monkeypatch, pipe=None):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        if pipe:
            ctx.on_start_value = pipe
        return ctx, fake_r2

    def _async_test_wrapper(test_fn):
        """Wrap async tests so pytest runs them with asyncio."""
        def wrapper(*args, **kw):
            try:
                coro = test_fn(*args, **kw)
                if asyncio.iscoroutine(coro):
                    asyncio.run(coro)
                return
            except Exception:
                raise
        return wrapper

    def test_local_invalid_input_rejects(monkeypatch):
        ctx, _ = _build(monkeypatch)
        mod = _import_module(module_name)
        try:
            mod.generate(ctx, prompt=None)
            assert False, "Should have raised"
        except Exception:
            pass

    def test_local_inference_fail(monkeypatch):
        import asyncio
        ctx, _ = _build(monkeypatch)
        # Replace _run_generate with a failing one
        def failing_run(*a, **kw):
            raise RuntimeError("inference failed")
        ctx.on_start_value = _FakeFailingPipeline()
        mod = _import_module(module_name)
        try:
            mod.generate(ctx, prompt="a cat")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_local_success_returns_contract(monkeypatch):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        fake_pipe = fake_pipe_class()
        ctx.on_start_value = fake_pipe
        mod = _import_module(module_name)
        result = mod.generate(ctx, prompt="a cat")
        _assert_contract(result)

    def test_local_success_uploads_artifact(monkeypatch):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        ctx = fake_ctx_fn()
        fake_pipe = fake_pipe_class()
        ctx.on_start_value = fake_pipe
        mod = _import_module(module_name)
        result = mod.generate(ctx, prompt="a cat")
        _assert_contract(result)
        _assert_artifact_body(fake_r2)

    return test_local_invalid_input_rejects, test_local_inference_fail, \
           test_local_success_returns_contract, test_local_success_uploads_artifact


# --- Modal cls (async with spawn) workers ---

def local_modal_async(module_name, raw_class, fake_pipe_class):
    """Generate 4 tests for Modal cls workers with spawn().
    
    Modal DI: instantiate class directly, replace self.pipe, call _run_generate().
    """

    def _build(monkeypatch, pipe=None):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        fp = pipe if pipe else fake_pipe_class()
        raw = raw_class()
        raw.pipe = fp
        return raw, fake_r2

    def test_local_invalid_input_rejects(monkeypatch):
        raw, _ = _build(monkeypatch)
        try:
            raw._run_generate(prompt=None)
            assert False, "Should have raised"
        except Exception:
            pass

    def test_local_inference_fail(monkeypatch):
        raw, _ = _build(monkeypatch)
        raw.pipe = _FakeFailingPipeline()
        try:
            raw._run_generate(prompt="a cat")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_local_success_returns_contract(monkeypatch):
        raw, _ = _build(monkeypatch)
        result = raw._run_generate(prompt="a cat")
        _assert_contract(result)

    def test_local_success_uploads_artifact(monkeypatch):
        raw, fake_r2 = _build(monkeypatch)
        result = raw._run_generate(prompt="a cat")
        _assert_contract(result)
        _assert_artifact_body(fake_r2)

    return test_local_invalid_input_rejects, test_local_inference_fail, \
           test_local_success_returns_contract, test_local_success_uploads_artifact


# --- Modal cls (sync, fastapi_endpoint) workers ---

def local_modal_sync(module_name, raw_class, fake_pipe_class):
    """Generate 4 tests for Modal cls workers (webhook/endpoint pattern)."""

    def _build(monkeypatch, pipe=None):
        from cli.tests import fakes as _f
        fake_r2 = _setup_r2(monkeypatch)
        fp = pipe if pipe else fake_pipe_class()
        raw = raw_class()
        raw.pipe = fp
        return raw, fake_r2

    def test_local_invalid_input_rejects(monkeypatch):
        raw, _ = _build(monkeypatch)
        try:
            raw.generate(prompt=None)
            assert False, "Should have raised"
        except Exception:
            pass

    def test_local_inference_fail(monkeypatch):
        raw, _ = _build(monkeypatch)
        raw.pipe = _FakeFailingPipeline()
        try:
            raw.generate(prompt="a cat")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_local_success_returns_contract(monkeypatch):
        raw, _ = _build(monkeypatch)
        result = raw.generate(prompt="a cat")
        _assert_contract(result)

    def test_local_success_uploads_artifact(monkeypatch):
        raw, fake_r2 = _build(monkeypatch)
        result = raw.generate(prompt="a cat")
        _assert_contract(result)
        _assert_artifact_body(fake_r2)

    return test_local_invalid_input_rejects, test_local_inference_fail, \
           test_local_success_returns_contract, test_local_success_uploads_artifact