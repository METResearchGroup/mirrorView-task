# Step 5: Experiment 2: train the modal adapter and infer on both test sets

## Scope

- **Caller:** operator running `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py`
- **Task:** Train the Experiment 2 full balanced modal LoRA adapter for 1 epoch on `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/data/chat_train.jsonl`, then run `infer_adapter` on both balanced test sets in one SageMaker job. Sync prediction CSVs locally and print invalid-rate and row-count checks (same pattern as Step 4).
- **Run id:** `part3_modal_001`
- **Differences from Step 4 only:** `--experiment experiment2_modal`, train file under `experiment2_modal/data/`, run id `part3_modal_001`, 1 epoch (set in `run_config.py`), preds under `experiment2_modal/preds/`.
- **Out of scope:** Code edits; Experiment 1 or 3 jobs; cross-eval scoring; training on test chat files.

## Dependencies

- Step 2 finished: data synced to S3, including `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/data/chat_train.jsonl` (~7,686 balanced rows).
- Step 3 finished: smoke job `part3_smoke_001` completed with parseable `keep`/`remove` outputs.
- Step 4 may run before, after, or in parallel with this step; Experiment 2 does not use Experiment 1 outputs.
- Env vars before launch: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`, `WANDB_API_KEY` (train only).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/steps/step4.md` | Operational pattern to mirror |
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md` | Decisions and pool table; run ids, epochs, S3 layout |
| `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/run_config.py` | Epoch count for Experiment 2 |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` | Prior timing (5,626 rows, 1 epoch, ~85 min) |
| `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py` | Train and infer CLI |

## Files allowed to change

- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/test_unanimous.csv`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/test_modal.csv`

## Files forbidden to change

- All code under `/workspace/`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/data/**`
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/data/**`
- Experiment 1 or 3 pred and adapter artifacts
- Adapters in git (S3 only)

## Main caller

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode train \
  --experiment experiment2_modal \
  --run-id part3_modal_001 \
  --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode infer_adapter \
  --experiment experiment2_modal \
  --run-id part3_modal_001 \
  --wait

aws s3 sync \
  s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/ \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python - <<'PY'
import json
from pathlib import Path
import pandas as pd

root = Path("/workspace/experiments/finetune_lora_phase2_part3_2026_09_24")
checks = {
    "test_unanimous": (
        root / "experiment2_modal/preds/test_unanimous.csv",
        root / "data/chat_test_unanimous.jsonl",
    ),
    "test_modal": (
        root / "experiment2_modal/preds/test_modal.csv",
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

Train and infer launcher stdout ends with `Completed`. Row check prints `match=True` for both test sets and invalid counts.

### Expected outputs

- Adapter S3: `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/adapters/part3_modal_001/`
- Preds local: `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/test_unanimous.csv` and `test_modal.csv`
- W&B: project `mirrorview-finetune-lora-phase2-part3`, run name contains `part3_modal_001`
- Train wall time: prior `experiments/larger_finetune_qwen_model_2026_08_08` used 5,626 rows x 1 epoch in ~85 min; union Experiment 2 has ~7,686 rows x 1 epoch, so expect ~117 min train and ~15 min infer on `ml.g5.xlarge`.

## Must pass

- Train and infer jobs for `part3_modal_001` complete without code edits.
- Adapter on S3; both pred CSVs synced; pred row counts match test chat JSONL line counts.
- Invalid counts printed; W&B run in `mirrorview-finetune-lora-phase2-part3`.
- One commit with only the two Experiment 2 pred CSVs.

## Must fail

- Code edits to rescue a failed job; training on test chat files or unanimous train data.
- Reusing `part3_modal_001` after partial failure; syncing preds from another experiment.
- Committing adapter weights to git.

## Implement-from-spec notes

Operational step: skip implement-from-spec Phases 2 through 5. One commit for the two `experiment2_modal/preds/` CSVs; message names `part3_modal_001`.
