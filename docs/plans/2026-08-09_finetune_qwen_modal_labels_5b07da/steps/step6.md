# Step 6: Upload data, run remote jobs, write RESULTS.md

## Goal

Execute the end-to-end remote teachability run for the modal-label experiment: upload frozen local data, ensure the ECR image is pushed, submit train then both inference jobs, sync prediction CSVs, and write `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` in the **same table shape** as PR #54.

**Hard gate:** do not start the paid `ml.g5.xlarge` train job until the user explicitly approves after confirming image push + data upload succeeded.

## Caller / unit of work

Operator checklist (commands below). Prefer reusing prior CLIs via the new wrappers; do not invent a parallel mega-script.

Sequence:

1. Confirm Step 2 data files exist and match contracts.
2. Upload `experiments/larger_finetune_qwen_model_2026_08_08/data/` → `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/`.
3. Build/tag/push ECR image `mirrorview-larger_finetune_qwen_model_2026_08_08:latest` in `us-east-2`.
4. Confirm Step 5 IAM allow-list is applied.
5. **STOP for user approval** to spend GPU.
6. Launch `--mode train --run-id <RUN_ID> --wait`.
7. Launch `--mode infer_baseline --run-id <RUN_ID> --wait`.
8. Launch `--mode infer_adapter --run-id <RUN_ID> --wait`.
9. Sync preds locally under `experiments/larger_finetune_qwen_model_2026_08_08/preds/`.
10. Run `evaluate.py --write-results .../RESULTS.md`.
11. Record run_id / job names / S3 URIs in the new README run record.

**Out of scope:** changing hyperparams mid-run; re-freezing with a new seed; editing the unanimous experiment’s RESULTS; local GPU as a substitute for SageMaker acceptance.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` | Operator commands |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Launch interface |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py` | RESULTS writer |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md` | Table shape to match |
| `/workspace/AGENTS.md` | `LAB_*` AWS credential export |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/preds/**` (synced artifacts)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (run record)
- `/workspace/CHANGELOG.md` (completion note)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- Locked training hyperparams / prompt text

## Contracts to freeze

### Upload

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

aws s3 sync experiments/larger_finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

aws s3 ls s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/
# must show: train.csv test.csv chat_train.jsonl chat_test.jsonl
```

### ECR push

Same login/tag/push pattern as the prior README, substituting repo name `mirrorview-larger_finetune_qwen_model_2026_08_08`.

### Launch

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_baseline --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_adapter --run-id <RUN_ID> --wait
```

Required env: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`; `WANDB_API_KEY` for train.

### RESULTS.md

Must include train and test tables for baseline vs fine-tuned with accuracy / precision / recall / F1 (positive class = remove), plus invalid-parse counts, matching the structure of `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`.

### Cost / size note

Modal balanced set is ~18× larger than the unanimous n=308 run (5626 vs 308). Expect longer train and infer wall time and higher GPU cost; still use `ml.g5.xlarge` unless the user explicitly revises instance type in a plan amendment.

## Exact commands (post-job evaluate)

```bash
aws s3 sync \
  s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/ \
  experiments/larger_finetune_qwen_model_2026_08_08/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/larger_finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Upload | Four data objects listed on new prefix | Wrote to unanimous prefix |
| Jobs | Train + both infers Complete | Failed / wrong image / PassRole |
| RESULTS | Tables present; remove = positive | Missing arms/splits |
| Isolation | Prior RESULTS/data untouched | Accidental edits to PR #54 artifacts |

## Done when

1. Remote train and both inference jobs completed for a recorded `run_id`.
2. `RESULTS.md` exists under the modal-labels experiment with the required tables.
3. README run record lists job names and S3/ECR URIs for this experiment only.
4. Unanimous experiment artifacts remain unchanged.
