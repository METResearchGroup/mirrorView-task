# Qwen3-4B LoRA fine-tune on modal keep/remove labels

Exploratory teachability check: can a larger class-balanced Study Phase 2 Part 2 modal keep/remove set teach `Qwen/Qwen3-4B-Instruct-2507` the task, using the same recipe as `experiments/finetune_qwen_model_2026_08_08` (pull request 54). Compare baseline vs fine-tuned tables. No numeric F1 success bar.

This package is a thin wrapper over that earlier experiment. It imports balance, split, prompt, train, inference, evaluate, and launcher helpers, and only changes the registry source, local paths, and cloud names.

## Design freeze

| Topic | Value |
|-------|-------|
| Goal | Teachability prelim on modal keep/remove labels; exploratory; no numeric F1 bar |
| Prior reference | Imports from `experiments/finetune_qwen_model_2026_08_08` |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared/data/registry.py` |
| Balance | all removes + equal keeps; `seed=1` (current data: 2813 + 2813 = 5626) |
| Split | 80/20; both splits 1:1 keep/remove; `seed=1` (current: train 4500 / test 1126) |
| Local outputs | `data/train.csv`, `data/test.csv`, `data/chat_train.jsonl`, `data/chat_test.jsonl` |
| Prompt | Same vendored rubric as prior experiment (imported, not recopied) |
| Train stack | TRL `SFTTrainer` + PEFT LoRA; assistant-only loss; bf16 LoRA (not QLoRA) |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05`, attn+MLP targets |
| Hyperparams | 1 epoch; lr `2e-4`; cosine + 3–5% warmup; batch 1 × grad accum 8; `max_seq_length=2048`; seed `1` |
| SageMaker | Custom Docker; modes `train` / `infer_baseline` / `infer_adapter`; `ml.g5.xlarge`; `us-east-2` |
| ECR | `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| S3 | bucket `mirrorview-experimental-artifacts`; prefix `mirrorview-larger_finetune_qwen_model_2026_08_08/` with `data/`, `adapters/<run_id>/`, `preds/{baseline,fine_tuned}/` |
| W&B | project `mirrorview-larger-finetune-qwen-2026-08-08` |
| Env | `HF_TOKEN` (required remote), `WANDB_API_KEY` via `EnvVarsContainer`, `SAGEMAKER_ROLE_ARN` for launch |
| Metrics | Local `evaluate.py` → `RESULTS.md`; positive class = remove |

## Install

```bash
uv sync --extra finetune-qwen-2026-08-08
```

## 1. Freeze local data

```bash
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force
```

## 2. Train / infer (local CLI; SageMaker uses the same entrypoints)

```bash
# Dry-run train config (no model download required)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_larger_dry \
  --dry-run

# Inference (baseline / adapter)
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_test.jsonl \
  --output-csv /tmp/larger_test_labels.csv \
  --mode baseline
```

## 3. Evaluate → RESULTS.md

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/larger_finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md
```

## 4. Docker image (repo-root context)

Base image: `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` (GPU / bf16 on `ml.g5.xlarge`).

```bash
docker build -f experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile \
  -t mirrorview-larger_finetune_qwen_model_2026_08_08:latest .

docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest train --help
docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest infer_baseline --help
docker run --rm mirrorview-larger_finetune_qwen_model_2026_08_08:latest infer_adapter --help
```

### ECR create / login / tag / push (`us-east-2`)

```bash
export AWS_REGION=us-east-2
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr describe-repositories \
  --repository-names mirrorview-larger_finetune_qwen_model_2026_08_08 \
  --region $AWS_REGION \
  || aws ecr create-repository \
       --repository-name mirrorview-larger_finetune_qwen_model_2026_08_08 \
       --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin \
      ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

docker tag mirrorview-larger_finetune_qwen_model_2026_08_08:latest \
  ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-larger_finetune_qwen_model_2026_08_08:latest

docker push \
  ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mirrorview-larger_finetune_qwen_model_2026_08_08:latest
```

## 5. Upload data + SageMaker launch

```bash
aws s3 sync experiments/larger_finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

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

Required env for launch: `SAGEMAKER_ROLE_ARN`, `HF_TOKEN`; `WANDB_API_KEY` required for `--mode train`.

If `CreateTrainingJob` fails with `iam:PassRole`, extend the execution-role Terraform under `experiments/finetune_qwen_model_2026_08_08/infra/` so the role can use this experiment's S3 prefix and ECR repo, then set `SAGEMAKER_ROLE_ARN` to the output ARN:

```bash
cd experiments/finetune_qwen_model_2026_08_08/infra
terraform init && terraform apply
```

Launcher dry-run (no submit):

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id dryrun_test --dry-run
```

## Run record

| Field | Value |
|-------|-------|
| Data S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/` |
| ECR image | `517478598677.dkr.ecr.us-east-2.amazonaws.com/mirrorview-larger_finetune_qwen_model_2026_08_08:latest` |
| `run_id` | `modal_larger_1ep_2026_08_09` |
| Exec role | IAM role `mirrorview-qwen-finetune-sm-exec` (via `SAGEMAKER_ROLE_ARN`) |
| Train job | `qwen-lora-train-2026-08-09-02-37-10-277` (Completed; 1 epoch) |
| Adapter S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/modal_larger_1ep_2026_08_09/` |
| Baseline infer | `qwen-lora-infer-baseline-2026-08-09-04-02-15-269` (Completed) |
| Adapter infer | `qwen-lora-infer-adapter-2026-08-09-04-32-44-609` (Completed) |
| Preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/{baseline,fine_tuned}/` |
| Results | `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` — test remove-F1 baseline **0.7210** → fine-tuned **0.6962**; accuracy 0.6385 → 0.7016 |
