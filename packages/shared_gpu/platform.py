"""Single source of truth for provider platform mechanics. No model imports."""
from __future__ import annotations

MODAL_HF_MOUNT = "/root/.cache/huggingface"
MODAL_VOLUME_NAME = "hf-cache"
BEAM_CACHE_PATH = "./hf-cache"
BEAM_VOLUME_NAME = "hf-cache"
FLASH_HF_HOME = "/runpod-volume/huggingface-cache"
HF_TRANSFER_ENV = "1"


def flash_hf_home() -> str:
    """Flash HF cache dir, honoring the runtime HF_HOME override."""
    import os

    return os.getenv("HF_HOME", FLASH_HF_HOME)


def modal_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Env dict for Modal images. Model extras (e.g. SDNQ flags) via `extra`."""
    env = {"HF_HOME": MODAL_HF_MOUNT, "HF_HUB_ENABLE_HF_TRANSFER": HF_TRANSFER_ENV}
    if extra:
        env.update(extra)
    return env


def beam_env(cache_path: str = BEAM_CACHE_PATH, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Env dict for Beam images. Model extras (e.g. SDNQ flags) via `extra`."""
    env = {"HF_HOME": cache_path, "HF_HUB_ENABLE_HF_TRANSFER": HF_TRANSFER_ENV}
    if extra:
        env.update(extra)
    return env


def flash_env(hf_home: str = FLASH_HF_HOME, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Env dict for Flash endpoints. Model extras (e.g. NVML flags) via `extra`."""
    env = {"HF_HOME": hf_home}
    if extra:
        env.update(extra)
    return env


def modal_volume():
    """Shared Modal hf-cache volume handle. Lazy import: only place allowed."""
    import modal

    return modal.Volume.from_name(MODAL_VOLUME_NAME, create_if_missing=True)


def beam_volume(mount_path: str = BEAM_CACHE_PATH):
    """Shared Beam hf-cache volume. Lazy import: only place allowed."""
    from beam import Volume

    return Volume(name=BEAM_VOLUME_NAME, mount_path=mount_path)
