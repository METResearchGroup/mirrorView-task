#!/usr/bin/env bash
# SageMaker dispatcher for experiment5 merge | infer (merged weights + vLLM).
set -euo pipefail

MODE="${1:-${MODE:-}}"
if [[ -z "${MODE}" ]]; then
  echo "Usage: entrypoint.sh <merge|infer|run> [...]" >&2
  exit 2
fi
shift || true

export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

PKG="/app/experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts"
SM_DATA_DIR="${SM_CHANNEL_DATA:-/opt/ml/input/data/data}"
SM_ADAPTER_DIR="${SM_CHANNEL_ADAPTER:-/opt/ml/input/data/adapter}"
SM_MERGED_DIR="${SM_CHANNEL_MERGED:-/opt/ml/input/data/merged}"
SM_MODEL_DIR="${SM_MODEL_DIR:-/opt/ml/model}"

MODEL_ID="${MODEL_ID:-Qwen/Qwen3.5-4B}"
MERGED_DIR="${MERGED_DIR:-${SM_MERGED_DIR}}"
ADAPTER_DIR="${ADAPTER_DIR:-${SM_ADAPTER_DIR}}"
CHAT_JSONL="${CHAT_JSONL:-${SM_DATA_DIR}/chat_all_posts.jsonl}"
OUTPUT_CSV="${OUTPUT_CSV:-${SM_MODEL_DIR}/all_posts.csv}"

case "${MODE}" in
  merge)
    exec python "${PKG}/merge_adapter.py" \
      --model-id "${MODEL_ID}" \
      --adapter-dir "${ADAPTER_DIR}" \
      --merged-dir "${MERGED_DIR}" \
      "$@"
    ;;
  infer)
    exec python "${PKG}/vllm_infer.py" \
      --chat-jsonl "${CHAT_JSONL}" \
      --model-dir "${MERGED_DIR}" \
      --output-csv "${OUTPUT_CSV}" \
      --model-id "${MODEL_ID}" \
      "$@"
    ;;
  run)
    python "${PKG}/merge_adapter.py" \
      --model-id "${MODEL_ID}" \
      --adapter-dir "${ADAPTER_DIR}" \
      --merged-dir "${MERGED_DIR}" \
      "$@"
    exec python "${PKG}/vllm_infer.py" \
      --chat-jsonl "${CHAT_JSONL}" \
      --model-dir "${MERGED_DIR}" \
      --output-csv "${OUTPUT_CSV}" \
      --model-id "${MODEL_ID}" \
      "$@"
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    echo "Expected: merge | infer | run" >&2
    exit 2
    ;;
esac
