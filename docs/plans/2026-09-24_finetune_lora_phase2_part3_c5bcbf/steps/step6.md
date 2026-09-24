# Step 6: Experiment 3: train the size-matched modal adapter and infer on both test sets

## Scope

- **Caller:** operator running `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py`
- **Task:** Train the Experiment 3 size-matched modal LoRA adapter for 3 epochs on `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/data/chat_train.jsonl`, then run `infer_adapter` on both balanced test sets. This experiment isolates the label rule: train row count and epoch count match Experiment 1 (~808 rows, 3 epochs), but labels are modal (drawn from Experiment 2 modal train posts, balanced to Experiment 1 remove and keep counts, seed 1).
- **Run id:** `part3_modal_sm_001`
- **Differences from Step 4 only:** `--experiment experiment3_modal_size_matched`, train file under `experiment3_modal_size_matched/data/`, run id `part3_modal_sm_001`, preds under `experiment3_modal_size_matched/preds/`. Epoch count is 3 (same as Experiment 1, not 1).
- **Out of scope:** Code edits; rescaling train size; cross-eval scoring.

## Dependencies

- Step 3 smoke passed (`part3_smoke_001`).
- Step 2 fixed all three train chat files and both test chat files. Step 6 can run in parallel with Steps 4 and 5 because train data for Experiment 3 was written in Step 2 and does not depend on Experiment 1 or 2 job outputs.
- Env vars: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`, `WANDB_API_KEY` (train only).

## Files to inspect (read-only)

- `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/steps/step4.md`
- `/tmp/p3_manifest.md` (Exp3 sampling rule)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/run_config.py`

## Files allowed to change

- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/test_unanimous.csv`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/test_modal.csv`

## Files forbidden to change

- All code under `/workspace/`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/data/**`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/data/**`
- Experiment 1 or 2 pred and adapter artifacts

## Main caller

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode train \
  --experiment experiment3_modal_size_matched \
  --run-id part3_modal_sm_001 \
  --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode infer_adapter \
  --experiment experiment3_modal_size_matched \
  --run-id part3_modal_sm_001 \
  --wait

aws s3 sync \
  s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/ \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python - <<'PY'
import json
from pathlib import Path
import pandas as pd

root = Path("/workspace/experiments/finetune_lora_phase2_part3_2026_09_24")
checks = {
    "test_unanimous": (
        root / "experiment3_modal_size_matched/preds/test_unanimous.csv",
        root / "data/chat_test_unanimous.jsonl",
    ),
    "test_modal": (
        root / "experiment3_modal_size_matched/preds/test_modal.csv",
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

Preflight: `wc -l` on Experiment 1 and Experiment 3 `chat_train.jsonl` must match (~808 lines each).

## Expected outputs

- Adapter S3: `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/adapters/part3_modal_sm_001/`
- Preds local: `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/test_unanimous.csv` and `test_modal.csv`
- W&B: project `mirrorview-finetune-lora-phase2-part3`, run name contains `part3_modal_sm_001`
- Train wall time: same as Experiment 1 (~808 rows x 3 epochs, ~47 min train, ~15 min infer). Prior row-scale reference: 308 rows x 3 epochs = ~18 min.

## Must pass

- Experiment 3 `chat_train.jsonl` line count matches Experiment 1 before launch.
- Jobs complete for `part3_modal_sm_001` without code edits; pred row counts match test JSONL.
- Invalid counts printed; W&B run exists. One commit for the two Experiment 3 pred CSVs.

## Must fail

- Changing row or epoch count to rescue a run; training on test chat files.
- Reusing `part3_modal_sm_001` after failed train; code edits mid-run.

## Implement-from-spec notes

Operational step. One git commit for the two `experiment3_modal_size_matched/preds/` CSVs only. Commit message names run id `part3_modal_sm_001` and notes the size-matched ablation (modal labels, Experiment 1 row and epoch counts).
