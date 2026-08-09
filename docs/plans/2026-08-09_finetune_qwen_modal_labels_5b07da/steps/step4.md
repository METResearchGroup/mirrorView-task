# Step 4: Docker image and SageMaker launcher for the new cloud names

## Goal

Add a custom Docker image and SageMaker launcher for `experiments/larger_finetune_qwen_model_2026_08_08/` that keep the three modes from pull request 54 (`train`, `infer_baseline`, and `infer_adapter`) on `ml.g5.xlarge` in `us-east-2`, while using the new ECR repository and S3 prefix. The image must copy both experiment packages so imports from `experiments.finetune_qwen_model_2026_08_08` resolve at runtime.

Do not submit paid GPU jobs in this step. Use launcher dry-run only. IAM prefix extension is Step 5, and the remote run is Step 6.

## Caller / unit of work

Build the image from the repo root.

```bash
docker build -f experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-larger_finetune_qwen_model_2026_08_08:latest .
```

Dry-run the launcher.

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_larger --dry-run
```

Work that is out of scope includes `terraform apply`, uploading data, and a full remote train.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/Dockerfile` | Base image and pip deps to mirror |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh` | Mode dispatch pattern |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Job config construction to wrap or import |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/.dockerignore` | Ignore patterns to adjust for copying both experiments |
| `/workspace/.dockerignore` | Repo-root dockerignore if present |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/.dockerignore` (and the root `.dockerignore` only if required for copying both experiments)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/tests/test_launch_sagemaker_config.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (build, push, and launch commands)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` only for minimal extraction of helpers that do not hardcode cloud names. The earlier launcher defaults must stay on the unanimous names.

## Files forbidden to change

- `/workspace/shared/**`
- The earlier experiment ECR and S3 constants used by the unanimous launcher's public defaults
- Step 5 Terraform, except for reading it

## Contracts to freeze

### Image

| Item | Value |
|------|-------|
| Base | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` |
| `PYTHONPATH` | `/app` |
| COPY | `shared/`, `lib/`, `experiments/finetune_qwen_model_2026_08_08/`, and `experiments/larger_finetune_qwen_model_2026_08_08/` |
| ENTRYPOINT | The new experiment `entrypoint.sh` |
| Modes | `train`, `infer_baseline`, and `infer_adapter` call the new experiment `train.py` or `inference.py` |
| Secrets | Never bake `HF_TOKEN` or `WANDB_API_KEY` into the image |

### Launcher cloud names

| Item | Value |
|------|-------|
| Region | `us-east-2` |
| Instance | `ml.g5.xlarge` |
| ECR repo | `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| S3 bucket | `mirrorview-experimental-artifacts` |
| S3 prefix | `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| Data URI | `s3://.../<prefix>/data` |
| Adapter URI | `s3://.../<prefix>/adapters/<run_id>` |
| Preds | `s3://.../<prefix>/preds/{baseline,fine_tuned}/` |
| Env injection | `HF_TOKEN` always, `WANDB_API_KEY` for train, and `SAGEMAKER_ROLE_ARN` required to submit |
| `--dry-run` | Print config and do not call `CreateTrainingJob` |

Prefer importing earlier launcher helpers such as `LaunchMode` and job-name builders, and override only the cloud name constants.

## Exact commands

```bash
cd /workspace

# Launcher dry-run (no AWS submit)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_larger --dry-run

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/larger_finetune_qwen_model_2026_08_08/tests/test_launch_sagemaker_config.py -q

# Docker build (when Docker available in the environment)
docker build -f experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-larger_finetune_qwen_model_2026_08_08:latest .

docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest train --help
docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest infer_baseline --help
docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest infer_adapter --help

# Confirm prior package is inside the image
docker run --rm --entrypoint python mirrorview-larger_finetune_qwen_model_2026_08_08:latest -c \
  "import experiments.finetune_qwen_model_2026_08_08, experiments.larger_finetune_qwen_model_2026_08_08; print('both packages OK')"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Dry-run URIs | New larger-experiment prefix and ECR only | Unanimous prefix used as the default |
| Image COPY | Both experiment packages importable | ImportError for the earlier package |
| Modes | Three `--help` paths exit 0 | A missing mode |
| Secrets | Not in image layers | Token files copied |

## Done when

1. Dockerfile and entrypoint exist for the new experiment.
2. Launcher dry-run and config tests pass with the new cloud names.
3. The image, when buildable, includes both experiment trees.
4. No paid SageMaker jobs have been submitted.
