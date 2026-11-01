MODAL_HF_MOUNT = "/root/.cache/huggingface"
MODAL_VOLUME_NAME = "worker-vision"
MODAL_IMAGE_IGNORE = (
    ".venv", "**/.venv/**", "__pycache__", "**/__pycache__/**",
    ".pytest_cache", "**/.pytest_cache/**", ".ruff_cache", "**/.ruff_cache/**",
    ".env", ".env.*", "**/.env", "**/.env.*", "tests", "tests/**", "fakes", "fakes/**",
)
BEAM_CACHE_PATH = "./hf-cache"
BEAM_VOLUME_NAME = "worker-vision"
FLASH_HF_HOME = "/runpod-volume/huggingface-cache"
def modal_env(extra=None):
    env = {"HF_HOME": MODAL_HF_MOUNT, "HF_XET_HIGH_PERFORMANCE": "1"}
    if extra:
        env.update(extra)
    return env
def beam_env(cache_path=BEAM_CACHE_PATH, extra=None):
    env = {"HF_HOME": cache_path, "HF_XET_HIGH_PERFORMANCE": "1"}
    if extra:
        env.update(extra)
    return env
def flash_env(hf_home=FLASH_HF_HOME, extra=None):
    env = {"HF_HOME": hf_home}
    if extra:
        env.update(extra)
    return env
def modal_volume():
    import modal
    return modal.Volume.from_name(MODAL_VOLUME_NAME, create_if_missing=True)
def beam_volume(mount_path=BEAM_CACHE_PATH):
    from beam import Volume
    return Volume(name=BEAM_VOLUME_NAME, mount_path=mount_path)
