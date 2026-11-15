FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    HF_HOME=/mnt/flux2-cache \
    FLUX2_MODEL_CACHE_DIR=/mnt/flux2-cache \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY shared ./shared
COPY dist ./dist
COPY worker_flux2_azure.py prefetch_model.py ./

EXPOSE 8080
CMD ["/opt/venv/bin/uvicorn", "worker_flux2_azure:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "30"]
