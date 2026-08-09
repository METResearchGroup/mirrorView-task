#!/usr/bin/env bash
# SageMaker / local container dispatcher for train | infer_baseline | infer_adapter.
set -euo pipefail

MODE="${1:-${MODE:-}}"
if [[ -z "${MODE}" ]]; then
  echo "Usage: entrypoint.sh <train|infer_baseline|infer_adapter> [...]" >&2
  exit 2
fi
shift || true

export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"
EXP_DIR="/app/experiments/finetune_qwen_model_2026_08_08"

SM_DATA_DIR="${SM_CHANNEL_DATA:-/opt/ml/input/data/data}"
SM_ADAPTER_DIR="${SM_CHANNEL_ADAPTER:-/opt/ml/input/data/adapter}"
SM_MODEL_DIR="${SM_MODEL_DIR:-/opt/ml/model}"

case "${MODE}" in
  train)
    if [[ "${1:-}" == "--help" ]]; then
      python "${EXP_DIR}/train.py" --help
      exit 0
    fi
    TRAIN_JSONL="${SM_DATA_DIR}/chat_train.jsonl"
    OUTPUT_DIR="${SM_MODEL_DIR}"
    exec python "${EXP_DIR}/train.py" \
      --train-jsonl "${TRAIN_JSONL}" \
      --output-dir "${OUTPUT_DIR}" \
      "$@"
    ;;
  infer_baseline)
    if [[ "${1:-}" == "--help" ]]; then
      python "${EXP_DIR}/inference.py" --help
      exit 0
    fi
    exec python "${EXP_DIR}/inference.py" \
      --mode baseline \
      --both-splits \
      --data-dir "${SM_DATA_DIR}" \
      --output-dir "${SM_MODEL_DIR}" \
      "$@"
    ;;
  infer_adapter)
    if [[ "${1:-}" == "--help" ]]; then
      python "${EXP_DIR}/inference.py" --help
      exit 0
    fi
    exec python "${EXP_DIR}/inference.py" \
      --mode adapter \
      --adapter-dir "${SM_ADAPTER_DIR}" \
      --both-splits \
      --data-dir "${SM_DATA_DIR}" \
      --output-dir "${SM_MODEL_DIR}" \
      "$@"
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    echo "Expected: train | infer_baseline | infer_adapter" >&2
    exit 2
    ;;
esac
