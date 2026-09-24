# syntax=docker/dockerfile:1
# Build from repo root:
#   docker build -f experiments/finetune_lora_phase2_part3_2026_09_24/Dockerfile \
#     -t mirrorview-finetune-lora-phase2-part3:latest .
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN echo "Part 3 Dockerfile scaffold"
