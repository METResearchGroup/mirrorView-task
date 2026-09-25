# syntax=docker/dockerfile:1
# Build from repo root:
#   docker build -f experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/Dockerfile \
#     -t mirrorview-finetune-lora-phase2-part3:vllm-all-posts .
FROM vllm/vllm-openai:v0.17.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install \
      "peft>=0.14.0" \
      "pandas>=2.2.0" \
      "boto3>=1.34.0"

COPY experiments/finetune_qwen_model_2026_08_08 /app/experiments/finetune_qwen_model_2026_08_08
COPY experiments/finetune_lora_phase2_part3_2026_09_24/__init__.py \
  /app/experiments/finetune_lora_phase2_part3_2026_09_24/__init__.py
COPY experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts \
  /app/experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts

RUN chmod +x /app/experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/entrypoint.sh

ENTRYPOINT ["/app/experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/entrypoint.sh"]
CMD []
