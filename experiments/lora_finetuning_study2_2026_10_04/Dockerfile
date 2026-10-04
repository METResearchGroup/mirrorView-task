# syntax=docker/dockerfile:1
# Build from the repo root:
#   docker build -f experiments/lora_finetuning_study2_2026_10_04/Dockerfile \
#     -t "$HF_JOB_IMAGE" .
#
# GPU image for LoRA SFT. Jobs pulls the tag produced by this build.
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/huggingface

WORKDIR /app

# Qwen3.5 linear attention falls back to a slow PyTorch reference unless both
# kernels import. This image is torch 2.6, CUDA 12.4, Python 3.11. The current
# flash-linear-attention release requires torch>=2.7, so pin 0.4.2 and install
# it without dependencies so pip does not replace the image's CUDA torch.
# causal-conv1d has no matching PyPI wheel; the GitHub wheel is the CXX11 ABI
# build used by the official PyTorch conda image.
RUN pip install --upgrade pip && \
    pip install \
      "transformers>=5.8.1" \
      "datasets>=3.0.0" \
      "accelerate>=1.0.0" \
      "peft>=0.14.0" \
      "trl>=0.15.0" \
      "wandb>=0.26.1" \
      "pandas>=3.0.2" \
      "pyarrow>=20.0.0" \
      "boto3>=1.42.88" \
      "python-dotenv>=1.2.2" \
      "pyyaml>=6.0" \
      "einops" && \
    pip install --no-deps \
      "flash-linear-attention==0.4.2" \
      "fla-core==0.4.2" \
      "https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.6.2.post1/causal_conv1d-1.6.2.post1+cu12torch2.6cxx11abiTRUE-cp311-cp311-linux_x86_64.whl"

COPY shared /app/shared
COPY lib /app/lib
COPY experiments/lora_finetuning_study2_2026_10_04 /app/experiments/lora_finetuning_study2_2026_10_04

CMD ["python", "experiments/lora_finetuning_study2_2026_10_04/train.py"]
