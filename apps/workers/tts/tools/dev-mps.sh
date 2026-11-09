#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "worker-tts:dev-mps requires an Apple Silicon Mac" >&2
  exit 1
fi

if [[ -z "${SECRET_HUGGINGFACE_TOKEN:-}" || -z "${TTS_AUDIO_SPEECH_API_KEY:-}" ]]; then
  echo "worker-tts:dev-mps requires the configured Hugging Face and TTS credentials" >&2
  exit 1
fi

uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python \
  fastapi==0.141.1 \
  librosa==0.10.0 \
  numpy==1.26.4 \
  resampy==0.4.3 \
  diffusers==0.29.0 \
  conformer==0.3.2 \
  safetensors==0.5.3 \
  pykakasi==2.3.0 \
  s3tokenizer==0.3.0 \
  soundfile==0.14.0 \
  spacy-pkuseg==1.0.1 \
  setuptools==80.9.0 \
  torch==2.6.0 \
  torchaudio==2.6.0 \
  transformers==4.46.3 \
  huggingface-hub[hf-transfer]==0.36.0 \
  hf_xet==1.6.0 \
  resemble-perth==1.0.1 \
  pyloudnorm==0.2.0 \
  omegaconf==2.3.0 \
  uvicorn==0.52.4
uv pip install --python .venv/bin/python --no-deps chatterbox-streaming==0.1.2

.venv/bin/python -c 'import torch; assert torch.backends.mps.is_available(), "PyTorch MPS is unavailable"'
export PYTHONPATH=.
exec .venv/bin/python -m uvicorn shared.worker_tts_audio_speech:build_app \
  --factory --host 127.0.0.1 --port 18764
