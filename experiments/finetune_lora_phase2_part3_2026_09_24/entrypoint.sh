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
PRIOR_DIR="/app/experiments/finetune_qwen_model_2026_08_08"

SM_DATA_DIR="${SM_CHANNEL_DATA:-/opt/ml/input/data/data}"
SM_ADAPTER_DIR="${SM_CHANNEL_ADAPTER:-/opt/ml/input/data/adapter}"
SM_MODEL_DIR="${SM_MODEL_DIR:-/opt/ml/model}"

MODEL_ID="${MODEL_ID:-}"
CHAT_TEMPLATE_KWARGS_JSON="${CHAT_TEMPLATE_KWARGS_JSON:-}"
NUM_TRAIN_EPOCHS="${NUM_TRAIN_EPOCHS:-}"

TRAIN_EXTRA_ARGS=()
INFER_EXTRA_ARGS=()
if [[ -n "${MODEL_ID}" ]]; then
  TRAIN_EXTRA_ARGS+=(--model-id "${MODEL_ID}")
  INFER_EXTRA_ARGS+=(--model-id "${MODEL_ID}")
fi
if [[ -n "${CHAT_TEMPLATE_KWARGS_JSON}" ]]; then
  TRAIN_EXTRA_ARGS+=(--chat-template-kwargs-json "${CHAT_TEMPLATE_KWARGS_JSON}")
  INFER_EXTRA_ARGS+=(--chat-template-kwargs-json "${CHAT_TEMPLATE_KWARGS_JSON}")
fi
if [[ -n "${NUM_TRAIN_EPOCHS}" ]]; then
  TRAIN_EXTRA_ARGS+=(--num-train-epochs "${NUM_TRAIN_EPOCHS}")
fi
if [[ "${SMOKE:-}" == "1" ]]; then
  TRAIN_EXTRA_ARGS+=(--max-steps 2)
  INFER_EXTRA_ARGS+=(--limit 5)
fi

case "${MODE}" in
  train)
    if [[ "${1:-}" == "--help" ]]; then
      python "${PRIOR_DIR}/train.py" --help
      exit 0
    fi
    TRAIN_JSONL="${SM_DATA_DIR}/chat_train.jsonl"
    OUTPUT_DIR="${SM_MODEL_DIR}"
    exec python "${PRIOR_DIR}/train.py" \
      --train-jsonl "${TRAIN_JSONL}" \
      --output-dir "${OUTPUT_DIR}" \
      "${TRAIN_EXTRA_ARGS[@]}" \
      "$@"
    ;;
  infer_baseline)
    if [[ "${1:-}" == "--help" ]]; then
      python "${PRIOR_DIR}/inference.py" --help
      exit 0
    fi
    python "${PRIOR_DIR}/inference.py" \
      --mode baseline \
      --chat-jsonl "${SM_DATA_DIR}/chat_test_unanimous.jsonl" \
      --output-csv "${SM_MODEL_DIR}/test_unanimous.csv" \
      "${INFER_EXTRA_ARGS[@]}" \
      "$@"
    exec python "${PRIOR_DIR}/inference.py" \
      --mode baseline \
      --chat-jsonl "${SM_DATA_DIR}/chat_test_modal.jsonl" \
      --output-csv "${SM_MODEL_DIR}/test_modal.csv" \
      "${INFER_EXTRA_ARGS[@]}" \
      "$@"
    ;;
  infer_adapter)
    if [[ "${1:-}" == "--help" ]]; then
      python "${PRIOR_DIR}/inference.py" --help
      exit 0
    fi
    python "${PRIOR_DIR}/inference.py" \
      --mode adapter \
      --adapter-dir "${SM_ADAPTER_DIR}" \
      --chat-jsonl "${SM_DATA_DIR}/chat_test_unanimous.jsonl" \
      --output-csv "${SM_MODEL_DIR}/test_unanimous.csv" \
      "${INFER_EXTRA_ARGS[@]}" \
      "$@"
    exec python "${PRIOR_DIR}/inference.py" \
      --mode adapter \
      --adapter-dir "${SM_ADAPTER_DIR}" \
      --chat-jsonl "${SM_DATA_DIR}/chat_test_modal.jsonl" \
      --output-csv "${SM_MODEL_DIR}/test_modal.csv" \
      "${INFER_EXTRA_ARGS[@]}" \
      "$@"
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    echo "Expected: train | infer_baseline | infer_adapter" >&2
    exit 2
    ;;
esac
