# syntax=docker/dockerfile:1
# Build from repo root:
#   docker build -f experiments/finetune_qwen_model_2026_08_08/Dockerfile \
#     -t mirrorview-finetune_qwen_model_2026_08_08:latest .
#
# GPU base suitable for bf16 on SageMaker ml.g5.xlarge.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install experiment Python deps (matches pyproject optional group intent).
RUN pip install --upgrade pip && \
    pip install \
      "transformers>=4.49.0" \
      "datasets>=3.0.0" \
      "accelerate>=1.0.0" \
      "peft>=0.14.0" \
      "trl>=0.15.0" \
      "scikit-learn>=1.5.0" \
      "wandb>=0.18.0" \
      "pyyaml>=6.0" \
      "pandas>=2.2.0" \
      "boto3>=1.34.0" \
      "sagemaker>=2.240.0,<3" \
      "python-dotenv>=1.0.0"

# Copy only what runtime needs (no secrets).
COPY shared /app/shared
COPY lib /app/lib
COPY experiments/finetune_qwen_model_2026_08_08 /app/experiments/finetune_qwen_model_2026_08_08

RUN chmod +x /app/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh

ENTRYPOINT ["/app/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh"]
# MODE is injected by launch_sagemaker.py via the job environment.
CMD []
