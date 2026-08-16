# Step 3: Launch unanimous adapter inference on the modal splits

## Goal

Implement `launch_sagemaker.py` so one SageMaker job runs adapter inference with the unanimous LoRA weights against the larger experiment modal chat data, and writes predictions to `preds/unanimous_lora/` on S3. Reuse the larger experiment ECR image and entrypoint. Do not build a new Docker image. Do not retrain.

## Caller / unit of work

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
# Prefer the Qwen exec role used by prior runs.
export SAGEMAKER_ROLE_ARN="${SAGEMAKER_ROLE_ARN:-arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec}"

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --dry-run
```

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` | `build_job_config`, `submit_job`, `JobConfig` |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Thin override pattern for cloud names |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh` | Confirms `infer_adapter` mounts adapter channel |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` | Existing S3 and ECR allow lists already cover needed prefixes |

## Files allowed to change

- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/tests/test_launch_sagemaker_config.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md` (commands only, if needed)

## Files forbidden to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` unless a dry-run or live submit proves the role cannot read or write a required URI
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile`
- Do not add a new Dockerfile under the comparison experiment

## Contracts

### Mode

Only one live mode is required: `infer_unanimous_adapter`.

### Resolved URIs (exact)

| Field | Value |
|-------|-------|
| Image | `517478598677.dkr.ecr.us-east-2.amazonaws.com/mirrorview-larger_finetune_qwen_model_2026_08_08:latest` |
| Entrypoint | `/app/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh` |
| Container args | `["infer_adapter"]` |
| Data channel | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data` |
| Adapter channel | Lean copy `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/unanimous_passrole_probe3_lean` (source weights remain under `.../adapters/passrole_probe3`) |
| Preds output / `PREDS_S3_URI` | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora` |
| Instance | `ml.g5.xlarge` |
| Region | `us-east-2` |

### Implementation rule

Call helpers from `experiments.finetune_qwen_model_2026_08_08.launch_sagemaker` (or the larger wrapper) for submit. After building a base `JobConfig` for adapter inference, override `adapter_s3_uri`, `output_s3_uri`, `data_s3_uri`, image, and entrypoint to the exact values above. Do not invent a new train mode.

### Dry-run test

`tests/test_launch_sagemaker_config.py` must assert the dry-run config uses the adapter URI ending in `adapters/unanimous_passrole_probe3_lean`, the preds URI ending in `preds/unanimous_lora`, and the larger ECR repo name.

## Pass / fail

Pass:

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/tests/test_launch_sagemaker_config.py -q

HF_TOKEN=dummy SAGEMAKER_ROLE_ARN=arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec \
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --dry-run
```

Expected dry-run stdout includes the adapter URI and `preds/unanimous_lora`.

Fail if the launcher points the adapter channel at the modal adapter, or if it requires building a new image.

## Out of scope

Live GPU spend (that is Step 4), syncing existing preds, writing RESULTS.md.
