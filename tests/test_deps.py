"""Dependency compatibility tests for GPU workers.

Creates temp venvs, installs exact dep lists, and verifies critical imports.
Run: pytest tests/test_deps.py -v
"""

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

WORKER_DEPS = {
    "flux2": [
        "torch==2.9.1",
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "diffusers==0.40.0",
        "sdnq==0.2.6",
        "huggingface_hub==1.29.0",
        "pillow==12.3.0",
    ],
    "krea2": [
        "torch==2.9.1",
        "diffusers==0.39.0",
        "transformers>=4.57,<5",
        "accelerate==1.14.0",
        "safetensors==0.8.0",
        "pillow==12.3.0",
        "protobuf==6.33.6",
        "opencv-python-headless==4.12.0.88",
        "peft==0.17.0",
    ],
}

IMPORT_CHECKS = {
    "flux2": textwrap.dedent("""\
        from diffusers.quantizers.auto import AUTO_QUANTIZER_MAPPING
        assert "sdnq" in AUTO_QUANTIZER_MAPPING, (
            f"sdnq not registered. Found: {list(AUTO_QUANTIZER_MAPPING.keys())}"
        )
        print("flux2: sdnq registered in diffusers")
    """),
    "krea2": textwrap.dedent("""\
        from diffusers import DiffusionPipeline
        print("krea2: DiffusionPipeline importable")
    """),
}


def _run_in_venv(packages: list[str], script: str) -> subprocess.CompletedProcess:
    """Create a temp venv, install packages, run a script."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )
        pip = str(venv_dir / "bin" / "pip")
        python = str(venv_dir / "bin" / "python")

        subprocess.run(
            [pip, "install", "--quiet", *packages],
            check=True,
            capture_output=True,
            text=True,
        )

        return subprocess.run(
            [python, "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )


@pytest.mark.parametrize("worker_name", ["flux2", "krea2"])
def test_deps_install_and_import(worker_name: str):
    """Verify pinned deps install and critical imports work."""
    packages = WORKER_DEPS[worker_name]
    script = IMPORT_CHECKS[worker_name]

    result = _run_in_venv(packages, script)

    assert result.returncode == 0, (
        f"{worker_name} dep check failed:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert f"{worker_name}:" in result.stdout
