import sys
import os
from pathlib import Path
import types

sys.path.insert(0, str(Path(__file__).parent))

_m = types.ModuleType("modal")

class _FakeVolume:
    @staticmethod
    def from_name(*a, **kw): return _FakeVolume()
    def commit(self): pass
    def reload(self): pass

class _FakeImage:
    @staticmethod
    def debian_slim(*a, **kw): return _FakeImage()
    def run_commands(self, *a, **kw): return self
    def pip_install(self, *a, **kw): return self
    def apt_install(self, *a, **kw): return self
    def env(self, *a, **kw): return self

class _FakeSecret:
    @staticmethod
    def from_dotenv(*a, **kw): return _FakeSecret()
    @staticmethod
    def from_dict(*a, **kw): return _FakeSecret()

class _FakeApp:
    def __init__(self, *a, **kw): pass
    def cls(self, *a, **kw): return lambda cls: cls

class _FakeCls:
    @staticmethod
    def from_name(*a, **kw): return _FakeCls()
    def remote(self, *a, **kw): return {}
    def local(self, *a, **kw): return self

class _FakeFunction:
    @staticmethod
    def from_name(*a, **kw): return _FakeFunction()
    def remote(self, *a, **kw): return {}

def _d(*a, **kw):
    def dec(f): return f
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
