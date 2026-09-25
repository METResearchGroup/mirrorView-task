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

_merge_transformers() {
  pip install -q "transformers>=5.8.1,<5.13"
}

_restore_vllm_transformers() {
  pip install -q "transformers==4.57.6" --force-reinstall
}

_fix_merged_config() {
  python3 <<'PY'
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

model_id = os.environ["MODEL_ID"]
token = os.environ.get("HF_TOKEN", "").strip() or None
merged = Path(os.environ["MERGED_DIR"])
hub_cfg = Path(hf_hub_download(model_id, "config.json", token=token))
(merged / "config.json").write_text(hub_cfg.read_text())
print(f"Refreshed {merged / 'config.json'} from {model_id}")
PY
}

case "${MODE}" in
  merge)
    _merge_transformers
    exec python3 "${PKG}/merge_adapter.py" \
      --model-id "${MODEL_ID}" \
      --adapter-dir "${ADAPTER_DIR}" \
      --merged-dir "${MERGED_DIR}" \
      "$@"
    ;;
  infer)
    exec python3 "${PKG}/vllm_infer.py" \
      --chat-jsonl "${CHAT_JSONL}" \
      --model-dir "${MERGED_DIR}" \
      --output-csv "${OUTPUT_CSV}" \
      --model-id "${MODEL_ID}" \
      "$@"
    ;;
  run)
    _merge_transformers
    python3 "${PKG}/merge_adapter.py" \
      --model-id "${MODEL_ID}" \
      --adapter-dir "${ADAPTER_DIR}" \
      --merged-dir "${MERGED_DIR}" \
      "$@"
    _fix_merged_config
    _restore_vllm_transformers
    exec python3 "${PKG}/vllm_infer.py" \
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
