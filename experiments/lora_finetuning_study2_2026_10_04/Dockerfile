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
      "pyyaml>=6.0"

COPY shared /app/shared
COPY lib /app/lib
COPY experiments/lora_finetuning_study2_2026_10_04 /app/experiments/lora_finetuning_study2_2026_10_04

CMD ["python", "experiments/lora_finetuning_study2_2026_10_04/train.py"]
