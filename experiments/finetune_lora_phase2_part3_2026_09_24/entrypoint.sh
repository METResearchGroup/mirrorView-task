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
EXP_DIR="/app/experiments/finetune_lora_phase2_part3_2026_09_24"
PRIOR_DIR="/app/experiments/finetune_qwen_model_2026_08_08"

SM_DATA_DIR="${SM_CHANNEL_DATA:-/opt/ml/input/data/data}"
SM_ADAPTER_DIR="${SM_CHANNEL_ADAPTER:-/opt/ml/input/data/adapter}"
SM_MODEL_DIR="${SM_MODEL_DIR:-/opt/ml/model}"

echo "Part 3 entrypoint stub: MODE=${MODE}" >&2
exit 2
