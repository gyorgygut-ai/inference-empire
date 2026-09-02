import sys
import types
from pathlib import Path

_root = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(_root / "shared"))

# --- Modal mock ---
_m = types.ModuleType("modal")


class _FakeVolume:
    @staticmethod
    def from_name(*a, **kw):
        return _FakeVolume()
    def commit(self):
        pass
    def reload(self):
        pass


class _FakeImage:
    @staticmethod
    def debian_slim(*a, **kw):
        return _FakeImage()
    def run_commands(self, *a, **kw):
        return self
    def pip_install(self, *a, **kw):
        return self
    def apt_install(self, *a, **kw):
        return self
    def env(self, *a, **kw):
        return self


class _FakeSecret:
    @staticmethod
    def from_dotenv(*a, **kw):
        return _FakeSecret()
    @staticmethod
    def from_dict(*a, **kw):
        return _FakeSecret()
    @staticmethod
    def from_name(*a, **kw):
        return _FakeSecret()


class _FakeApp:
    def __init__(self, *a, **kw):
        pass
    def cls(self, *a, **kw):
        return lambda cls: cls
    def local_entrypoint(self, *a, **kw):
        def dec(f):
            return f
        return dec


class _FakeCls:
    @staticmethod
    def from_name(*a, **kw):
        return _FakeCls()
    def remote(self, *a, **kw):
        return {}
    def local(self, *a, **kw):
        return self


class _FakeFunction:
    @staticmethod
    def from_name(*a, **kw):
        return _FakeFunction()
    def remote(self, *a, **kw):
        return {}


def _d(*a, **kw):
    def dec(f):
        return f
    return dec


_m.Volume = _FakeVolume
_m.Image = _FakeImage
_m.Secret = _FakeSecret
_m.App = _FakeApp
_m.Cls = _FakeCls
_m.Function = _FakeFunction
_m.method = _d
_m.enter = _d
_m.fastapi_endpoint = _d

sys.modules["modal"] = _m

# --- Beam mock ---
beam_mock = types.ModuleType("beam")


class _FakeBeamImage:
    def __init__(self, **kw):
        pass
    def add_python_packages(self, pkgs):
        return self
    def with_envs(self, envs):
        return self
    def add_commands(self, cmds):
        return self
    @staticmethod
    def from_registry(*a, **kw):
        return _FakeBeamImage()


beam_mock.Image = _FakeBeamImage
beam_mock.QueueDepthAutoscaler = type("QueueDepthAutoscaler", (), {"__init__": lambda s, **kw: None})
beam_mock.Volume = type("Volume", (), {"__init__": lambda s, **kw: None})
beam_mock.task_queue = lambda **kw: lambda f: f
beam_mock.endpoint = lambda **kw: lambda f: f

sys.modules["beam"] = beam_mock
