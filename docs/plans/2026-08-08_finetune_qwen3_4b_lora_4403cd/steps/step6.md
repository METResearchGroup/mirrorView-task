# Step 6: Package custom Docker image and ECR push path

## Goal

Add a production Dockerfile for this experiment (repo-root build context), document build/tag/push to ECR `mirrorview-finetune_qwen_model_2026_08_08` in `us-east-2`, and verify the image can start the three entrypoint modes (`train`, `infer_baseline`, `infer_adapter`) via a single container command interface.

Do **not** submit SageMaker jobs in this step (launcher is Step 7; paid GPU train is Step 8).

## Caller / unit of work

**Main caller:** operator building and pushing the image from repo root.

```text
docker build -f experiments/finetune_qwen_model_2026_08_08/Dockerfile -t mirrorview-finetune_qwen_model_2026_08_08:latest .
```

Container entrypoint contract:

```text
python /app/experiments/finetune_qwen_model_2026_08_08/<train|inference>.py ...
```

or a thin `/app/entrypoint.sh <mode> ...` that dispatches:

| Mode | Invokes |
|------|---------|
| `train` | `train.py` |
| `infer_baseline` | `inference.py --mode baseline` |
| `infer_adapter` | `inference.py --mode adapter` |

Image must include enough of the repo for `PYTHONPATH=/app` imports of `experiments.finetune_qwen_model_2026_08_08`, `shared`, and `lib`.

**Out of scope:** `launch_sagemaker.py`; uploading data; full model training inside `docker build`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` | Runtime deps / CLI |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` | Runtime deps / CLI |
| `/workspace/pyproject.toml` | Extra `finetune-qwen-2026-08-08` |
| `/workspace/docs/runbooks/AWS_DEPLOYMENT_GUIDE.md` | AWS account/region conventions if any |
| AWS ECR docs for `us-east-2` login/push | Exact CLI |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/Dockerfile`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh` (optional)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/.dockerignore` (optional; must not exclude `shared/` / `lib/` / experiment code needed at runtime)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (build/push commands)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/requirements.docker.txt` only if pinning image deps separately from uv extra (prefer one source of truth)

## Files forbidden to change

- `/workspace/shared/**` contents (may be COPY’d into image; do not edit sources)
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- Do not bake secrets (`HF_TOKEN`, `WANDB_API_KEY`) into layers

## Contracts to freeze

### Image

| Item | Value |
|------|-------|
| Build context | repo root |
| Dockerfile path | `experiments/finetune_qwen_model_2026_08_08/Dockerfile` |
| Region | `us-east-2` |
| ECR repo name | `mirrorview-finetune_qwen_model_2026_08_08` |
| Runtime | GPU-capable base suitable for PyTorch bf16 on `ml.g5.xlarge` (document chosen base tag in README) |
| Code layout in image | `/app` as repo root equivalent; `PYTHONPATH=/app` |
| Secrets | runtime env only |

### ECR bootstrap

README must document:

1. Create ECR repository if missing (name exact above).
2. `aws ecr get-login-password --region us-east-2 | docker login ...`
3. Tag with account registry URI.
4. `docker push`.

### Smoke without GPU train

`docker run --rm <image> <mode> --help` (or equivalent) exits 0 for all three modes.

## Exact commands

```bash
cd /workspace

docker build -f experiments/finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-finetune_qwen_model_2026_08_08:latest .

# Mode help smokes (entrypoint shape may vary; adjust to implemented interface):
docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest train --help
docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest infer_baseline --help
docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest infer_adapter --help
```

ECR push (requires AWS creds; create repo once):

```bash
export AWS_REGION=us-east-2
# ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
# aws ecr describe-repositories --repository-names mirrorview-finetune_qwen_model_2026_08_08 --region $AWS_REGION \
#   || aws ecr create-repository --repository-name mirrorview-finetune_qwen_model_2026_08_08 --region $AWS_REGION
# aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
# docker tag mirrorview-finetune_qwen_model_2026_08_08:latest ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-finetune_qwen_model_2026_08_08:latest
# docker push ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-finetune_qwen_model_2026_08_08:latest
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| `docker build` | exit 0 | Build error |
| Mode help | three modes respond | Missing mode |
| Secrets | none in image history/env defaults | Token baked in |
| Context | build from repo root works | Requires experiment-only context |
| ECR docs | README has exact repo/region | Vague “push to ECR” |

## Done when

1. Dockerfile builds from repo root.
2. Three modes are invocable in the container.
3. README documents ECR create/login/tag/push for `us-east-2` / `mirrorview-finetune_qwen_model_2026_08_08`.
4. No SageMaker training job submitted in this step.
