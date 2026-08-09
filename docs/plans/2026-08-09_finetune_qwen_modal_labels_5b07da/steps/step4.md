# Step 4: Docker image and SageMaker launcher for the new identity

## Goal

Add a custom Docker image and SageMaker launcher for `experiments/larger_finetune_qwen_model_2026_08_08/` that preserve PR #54’s three modes (`train` / `infer_baseline` / `infer_adapter`) on `ml.g5.xlarge` in `us-east-2`, but use the **new** ECR repo and S3 prefix. The image **must copy both** experiment packages so imports from `experiments.finetune_qwen_model_2026_08_08` resolve at runtime.

Do **not** submit paid GPU jobs in this step (dry-run launcher only). IAM prefix extension is Step 5; remote run is Step 6.

## Caller / unit of work

**Docker (repo-root context):**

```bash
docker build -f experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-larger_finetune_qwen_model_2026_08_08:latest .
```

**Launcher dry-run:**

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_modal --dry-run
```

**Out of scope:** `terraform apply`; uploading data; full remote train.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/Dockerfile` | Base image + pip deps to mirror |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh` | Mode dispatch pattern |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Job config construction to wrap/import |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/.dockerignore` | Ignore patterns; adjust for dual COPY |
| `/workspace/.dockerignore` | Repo-root dockerignore if present |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/.dockerignore` (and/or root `.dockerignore` only if required for dual-experiment COPY)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/tests/test_launch_sagemaker_config.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (build/push/launch commands)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` **only** for minimal extraction of identity-free helpers (prior defaults must stay unanimous)

## Files forbidden to change

- `/workspace/shared/**`
- Prior experiment ECR/S3 identity constants as used by the unanimous launcher’s public defaults
- Step 5 Terraform (except read)

## Contracts to freeze

### Image

| Item | Value |
|------|-------|
| Base | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` |
| `PYTHONPATH` | `/app` |
| COPY | `shared/`, `lib/`, `experiments/finetune_qwen_model_2026_08_08/`, `experiments/larger_finetune_qwen_model_2026_08_08/` |
| ENTRYPOINT | new experiment `entrypoint.sh` |
| Modes | `train`, `infer_baseline`, `infer_adapter` → new experiment `train.py` / `inference.py` |
| Secrets | never bake `HF_TOKEN` / `WANDB_API_KEY` into the image |

### Launcher identity

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
| Env injection | `HF_TOKEN` always; `WANDB_API_KEY` for train; `SAGEMAKER_ROLE_ARN` required to submit |
| `--dry-run` | print config; no `CreateTrainingJob` |

Prefer importing prior launcher helpers (`LaunchMode`, job-name builders, etc.) and overriding only identity constants.

## Exact commands

```bash
cd /workspace

# Launcher dry-run (no AWS submit)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_modal --dry-run

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
| Dry-run URIs | New modal prefix/ECR only | Unanimous prefix leaked as default |
| Image COPY | Both experiment packages importable | ImportError for prior package |
| Modes | Three `--help` paths exit 0 | Missing mode |
| Secrets | Not in image layers | Token files copied |

## Done when

1. Dockerfile + entrypoint exist for the new experiment.
2. Launcher dry-run and config tests pass with the new identity.
3. Image (when buildable) includes both experiment trees.
4. No paid SageMaker jobs submitted.
