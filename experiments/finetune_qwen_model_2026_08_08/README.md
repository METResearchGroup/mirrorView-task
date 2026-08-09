# Qwen3-4B LoRA fine-tune (keep/remove teachability)

Exploratory prelim: can a small, high-purity, class-balanced Study Phase 2 Part 2 keep/remove set teach `Qwen/Qwen3-4B-Instruct-2507` the task at all, before collecting more labels. Compare baseline vs fine-tuned tables. No numeric F1 success bar.

## Design freeze

| Topic | Value |
|-------|-------|
| Goal | Teachability prelim; exploratory; no numeric F1 bar |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` via `shared/data/registry.py` |
| Balance | all 154 removes + 154 keeps; `seed=1` |
| Split | 80/20; both splits 1:1 keep/remove; `seed=1` |
| Local outputs | `data/train.csv`, `data/test.csv`, `data/chat_train.jsonl`, `data/chat_test.jsonl` |
| Prompt | Vendored rubric; closing asks for `keep`/`remove` only; Post 1 = original, Post 2 = mirror |
| Train stack | TRL `SFTTrainer` + PEFT LoRA; assistant-only loss; bf16 LoRA (not QLoRA) |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05`, attn+MLP targets |
| Hyperparams | 3 epochs; lr `2e-4`; cosine + 3–5% warmup; batch 1 × grad accum 8; `max_seq_length=2048`; seed `1` |
| SageMaker | Custom Docker; modes `train` / `infer_baseline` / `infer_adapter`; `ml.g5.xlarge`; `us-east-2` |
| ECR | `mirrorview-finetune_qwen_model_2026_08_08` |
| S3 | bucket `mirrorview-experimental-artifacts`; prefix `mirrorview-finetune_qwen_model_2026_08_08/` with `data/`, `adapters/<run_id>/`, `preds/{baseline,fine_tuned}/` |
| Env | `HF_TOKEN` (required remote), `WANDB_API_KEY` via `EnvVarsContainer`, `SAGEMAKER_ROLE_ARN` for launch |
| Metrics | Local `evaluate.py` → `RESULTS.md`; positive class = remove |

## Install

```bash
uv sync --extra finetune-qwen-2026-08-08
```

## 1. Freeze local data

```bash
PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force
```

## 2. Train / infer (local CLI; SageMaker uses the same entrypoints)

```bash
# Dry-run train config (no model download required)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_dry \
  --dry-run

# Inference (baseline / adapter)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_test.jsonl \
  --output-csv /tmp/test_labels.csv \
  --mode baseline
```

## 3. Evaluate → RESULTS.md

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/finetune_qwen_model_2026_08_08/RESULTS.md
```

## 4. Docker image (repo-root context)

Base image: `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` (GPU / bf16 on `ml.g5.xlarge`).

```bash
docker build -f experiments/finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-finetune_qwen_model_2026_08_08:latest .

docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest train --help
docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest infer_baseline --help
docker run --rm mirrorview-finetune_qwen_model_2026_08_08:latest infer_adapter --help
```

### ECR create / login / tag / push (`us-east-2`)

```bash
export AWS_REGION=us-east-2
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr describe-repositories \
  --repository-names mirrorview-finetune_qwen_model_2026_08_08 \
  --region $AWS_REGION \
  || aws ecr create-repository \
       --repository-name mirrorview-finetune_qwen_model_2026_08_08 \
       --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin \
      ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

docker tag mirrorview-finetune_qwen_model_2026_08_08:latest \
  ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-finetune_qwen_model_2026_08_08:latest

docker push \
  ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-finetune_qwen_model_2026_08_08:latest
```

## 5. Upload data + SageMaker launch

```bash
aws s3 sync experiments/finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_baseline --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_adapter --run-id <RUN_ID> --wait
```

Required env for launch: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`; `WANDB_API_KEY` required for `--mode train`.

If `CreateTrainingJob` fails with `iam:PassRole`, apply the execution-role Terraform under `infra/` (requires IAM write access), then set `SAGEMAKER_ROLE_ARN` to the output ARN:

```bash
cd experiments/finetune_qwen_model_2026_08_08/infra
terraform init && terraform apply
```

Launcher dry-run (no submit):

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_test --dry-run
```

## Run record

| Field | Value |
|-------|-------|
| Data S3 | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/` |
| ECR image | `517478598677.dkr.ecr.us-east-2.amazonaws.com/mirrorview-finetune_qwen_model_2026_08_08:latest` |
| `run_id` | `passrole_probe3` |
| Exec role | IAM role `mirrorview-qwen-finetune-sm-exec` (via `SAGEMAKER_ROLE_ARN`) |
| Train job | `qwen-lora-train-2026-08-09-00-40-25-347` (Completed) |
| Adapter S3 | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/adapters/passrole_probe3/` |
| Baseline infer | `qwen-lora-infer-baseline-2026-08-09-00-58-57-462` (Completed) |
| Adapter infer | `qwen-lora-infer-adapter-2026-08-09-01-08-09-472` (Completed) |
| Preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/preds/{baseline,fine_tuned}/` |
| Results | `experiments/finetune_qwen_model_2026_08_08/RESULTS.md` — test remove-F1 baseline **0.7407** → fine-tuned **0.9688** (0 invalids) |
