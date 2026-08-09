# Step 7: SageMaker launcher for train and both infer modes

## Goal

Implement `experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` to submit SageMaker Training jobs that run the custom ECR image in one of three modes on `ml.g5.xlarge` in `us-east-2`, with correct S3 channels/env injection. Do **not** run the full paid train+infer campaign until Step 8 approval — this step gates on launcher dry validation and, optionally, a non-GPU/no-op submit refusal path.

## Caller / unit of work

**Main caller:**

```text
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train \
  --run-id <RUN_ID>
```

Modes: `train` | `infer_baseline` | `infer_adapter`.

Happy path per mode:

1. Require `SAGEMAKER_ROLE_ARN`.
2. Require `HF_TOKEN` in environment (fail fast); pass into job env.
3. For `train`: require `WANDB_API_KEY` via `EnvVarsContainer.get_env_var(..., required=True)`; pass into job env.
4. Resolve image URI for ECR repo `mirrorview-finetune_qwen_model_2026_08_08` in `us-east-2`.
5. Point inputs at `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/`.
6. For `train`: output adapter under `.../adapters/<run_id>/`.
7. For infer modes: write preds under `.../preds/{baseline|fine_tuned}/` (`train_labels.csv` / `test_labels.csv` — job may write both splits in one infer invocation **or** require `--split {train,test}`; pick one and document; prefer **one infer job writes both train and test CSVs** for that arm).
8. For `infer_adapter`: read adapter from `.../adapters/<run_id>/`.
9. Instance type `ml.g5.xlarge`; region `us-east-2`.
10. Print job name and S3 URIs; exit 0 on successful submit.

Support `--dry-run` that prints the estimator/job config without calling `fit()`.

**Out of scope:** building Docker (Step 6); uploading data (Step 8); local RESULTS generation beyond printing paths.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/modernbert/launch_sagemaker.py` | Role/W&B injection, run_id, wait flag precedents — **do not copy HF estimator**; use custom image estimator (`sagemaker.estimator.Estimator` or equivalent) |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/Dockerfile` | Entry command expectations |
| `/workspace/lib/load_env_vars.py` | W&B key loading |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (launch commands)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_launch_sagemaker_config.py` (pure config construction tests; mock boto3)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_2026_07_01/models/modernbert/**`
- `/workspace/shared/**`
- Do not hardcode AWS account IDs in git if avoidable — resolve via STS at launch time

## Contracts to freeze

### S3 layout

Base: `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/`

| Path | Contents |
|------|----------|
| `data/` | `train.csv`, `test.csv`, `chat_train.jsonl`, `chat_test.jsonl` |
| `adapters/<run_id>/` | LoRA adapter from train |
| `preds/baseline/train_labels.csv` | Baseline train preds |
| `preds/baseline/test_labels.csv` | Baseline test preds |
| `preds/fine_tuned/train_labels.csv` | Adapter train preds |
| `preds/fine_tuned/test_labels.csv` | Adapter test preds |

### Job env

| Variable | Modes |
|----------|-------|
| `HF_TOKEN` | all |
| `WANDB_API_KEY` | `train` required |
| `RUN_ID` | all |
| Mode dispatch | CLI args to container entrypoint |

### Instance / region

| Field | Value |
|-------|-------|
| `instance_type` | `ml.g5.xlarge` |
| `region` | `us-east-2` |

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/finetune_qwen_model_2026_08_08/tests/test_launch_sagemaker_config.py -q

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_test --dry-run
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Dry-run | Prints image, instance, S3 paths, mode; no `fit()` | Submits real job accidentally |
| Missing role | Clear error | Boto obscure failure |
| Missing HF_TOKEN | Fail before submit | Submit without token |
| Mode enum | Only three modes | Silent typos |
| Pred paths | baseline vs fine_tuned prefixes correct | Wrong arm folder |

## Done when

1. Launcher implements three modes with frozen S3/env/instance contracts.
2. Dry-run + unit tests pass without submitting jobs.
3. README documents the three launch commands and required env vars.
