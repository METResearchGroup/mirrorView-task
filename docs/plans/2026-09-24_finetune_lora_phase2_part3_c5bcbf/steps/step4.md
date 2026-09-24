# Step 4: Experiment 1: train the unanimous adapter and infer on both test sets

## Scope

- **Caller:** operator running `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py`
- **Task:** Train the Experiment 1 unanimous LoRA adapter for 3 epochs on `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/data/chat_train.jsonl`, then run `infer_adapter` to score both balanced test chat files in one SageMaker job. Sync prediction CSVs locally. Record invalid rate and row-count checks. Do not score cross-eval or write `RESULTS.md` (Step 7).
- **Run id:** `part3_uni_001`
- **Out of scope:** Editing Python, Terraform, Docker, or data files; training on test chat files; reusing a prior run id; Experiment 2 or 3 jobs.

## Dependencies

- Step 2 finished: split manifest, train CSVs, chat JSONL files, and shared test chat files exist under `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/` and are synced to `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/`.
- Step 3 finished: ECR image `mirrorview-finetune-lora-phase2-part3:latest` is pushed; smoke job `part3_smoke_001` completed with parseable `keep`/`remove` outputs.
- Env vars set before launch: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`, `WANDB_API_KEY` (train only).

## Files to inspect (read-only)

- `/tmp/p3_manifest.md` (run ids, epochs, S3 layout)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/run_config.py`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/entrypoint.sh`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (prior timing)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` (`__invalid__` contract)

## Files allowed to change

- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/test_unanimous.csv` (synced from S3)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/test_modal.csv` (synced from S3)

## Files forbidden to change

- All Python, shell, Dockerfile, Terraform, and test files under `/workspace/`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/data/**`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/data/**` (shared test files)
- Prediction or adapter objects for Experiments 2, 3, or 4
- Adapters in git (S3 only)

## Main caller

Export credentials and region, then launch train and infer from `/workspace`:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode train \
  --experiment experiment1_unanimous \
  --run-id part3_uni_001 \
  --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode infer_adapter \
  --experiment experiment1_unanimous \
  --run-id part3_uni_001 \
  --wait

aws s3 sync \
  s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/ \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python - <<'PY'
import json
from pathlib import Path
import pandas as pd

root = Path("/workspace/experiments/finetune_lora_phase2_part3_2026_09_24")
checks = {
    "test_unanimous": (
        root / "experiment1_unanimous/preds/test_unanimous.csv",
        root / "data/chat_test_unanimous.jsonl",
    ),
    "test_modal": (
        root / "experiment1_unanimous/preds/test_modal.csv",
        root / "data/chat_test_modal.jsonl",
    ),
}
for name, (pred_path, chat_path) in checks.items():
    n_pred = len(pd.read_csv(pred_path))
    n_test = sum(1 for _ in chat_path.open())
    invalid = (pd.read_csv(pred_path)["predicted_decision"] == "__invalid__").sum()
    print(f"{name}: pred_rows={n_pred} test_rows={n_test} match={n_pred == n_test} invalid={invalid}")
PY
```

Expected train launcher stdout ends with job status `Completed`. Infer launcher stdout ends with `Completed`. Row-check prints `match=True` for both test sets and reports `invalid` counts.

## Expected outputs

- Adapter S3: `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/adapters/part3_uni_001/`
- Preds S3: `.../experiment1_unanimous/preds/test_unanimous.csv` and `test_modal.csv`
- Preds local: `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/test_unanimous.csv` and `test_modal.csv`
- W&B: project `mirrorview-finetune-lora-phase2-part3`, run name contains `part3_uni_001`
- Train wall time: prior `experiments/finetune_qwen_model_2026_08_08` used 308 rows x 3 epochs in ~18 min; Part 3 Experiment 1 has ~808 rows x 3 epochs, so expect ~47 min train and ~15 min infer on `ml.g5.xlarge`.

## Must pass

- Train and infer jobs for `part3_uni_001` complete without code edits.
- Adapter on S3; both pred CSVs synced; row counts match test chat JSONL line counts.
- Invalid counts printed; W&B train run in `mirrorview-finetune-lora-phase2-part3`.
- One commit with only the two Experiment 1 pred CSVs.

## Must fail

- Code edits to rescue a failed job; training on test chat files.
- Reusing `part3_uni_001` after partial failure; syncing preds from another experiment.
- Committing adapter weights to git.

## Implement-from-spec notes

Operational step: skip implement-from-spec Phases 2 through 5. One commit for the two `experiment1_unanimous/preds/` CSVs; message names `part3_uni_001`.
