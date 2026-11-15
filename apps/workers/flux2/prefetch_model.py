"""Download the Flux 2 model into the mounted persistent cache."""

import os
from pathlib import Path

from shared.worker_flux2 import download_models


def main() -> None:
    cache_dir = Path(os.environ.get("FLUX2_MODEL_CACHE_DIR", "/mnt/flux2-cache"))
    models = download_models(cache_dir=cache_dir)
    for name, snapshot in models.items():
        files = [path for path in snapshot.rglob("*") if path.is_file()]
        if not files:
            raise RuntimeError(f"Model cache is empty for {name}: {snapshot}")
        print(f"Cached {name}: {len(files)} files at {snapshot}", flush=True)


if __name__ == "__main__":
    main()
