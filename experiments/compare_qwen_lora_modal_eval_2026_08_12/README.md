# Compare three Qwen keep/remove arms on one modal-label eval set

Pull requests 54 and 57 each trained a LoRA adapter, but each reported metrics on a different labeled set. This experiment scores three arms on the same frozen modal keep/remove splits:

1. `baseline`: base `Qwen/Qwen3-4B-Instruct-2507` with no LoRA
2. `unanimous_lora`: adapter from pull request 54 (`passrole_probe3`), trained on unanimous min-3 labels
3. `modal_lora`: adapter from pull request 57 (`modal_larger_1ep_2026_08_09`), trained on modal labels

No retraining happens here. Evaluation reuses the frozen chat files from `experiments/larger_finetune_qwen_model_2026_08_08/data/`, which come from registry entry `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`.

## Design freeze

| Topic | Value |
|-------|-------|
| Goal | Same-dataset comparison of baseline, unanimous LoRA, and modal LoRA |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Eval data | Frozen files in `experiments/larger_finetune_qwen_model_2026_08_08/data/` from `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| Eval rows | Balanced 1:1 modal splits; seed 1; train 4500 / test 1126 |
| Arms | `baseline`, `unanimous_lora`, `modal_lora` |
| Pred layout | `preds/{baseline,unanimous_lora,modal_lora}/{train,test}_labels.csv` |
| Metrics | Accuracy, precision, recall, F1; positive class = remove |
| Remote image | Reuse ECR `mirrorview-larger_finetune_qwen_model_2026_08_08:latest` |
| Modal data S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/` |
| Unanimous adapter source | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/adapters/passrole_probe3/` |
| Unanimous adapter infer channel | Lean copy at `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/unanimous_passrole_probe3_lean/` |
| Existing preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/{baseline,fine_tuned}/` |
| New preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora/` |
| Env | `HF_TOKEN`, `SAGEMAKER_ROLE_ARN` (prefer `mirrorview-qwen-finetune-sm-exec`) |

## Install

```bash
uv sync --extra finetune-qwen-2026-08-08
```

## 1. Sync existing baseline and modal preds

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --force
```

## 2. Infer the unanimous adapter on the modal splits

```bash
export SAGEMAKER_ROLE_ARN=arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --wait
```

Dry-run (no submit):

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --dry-run
```

## 3. Download unanimous preds and write RESULTS.md

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --include-unanimous \
  --force

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --write-results experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
```

## Run record

| Field | Value |
|-------|-------|
| Eval data | `experiments/larger_finetune_qwen_model_2026_08_08/data/` |
| Unanimous adapter (source) | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/adapters/passrole_probe3/` |
| Unanimous adapter (lean infer channel) | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/unanimous_passrole_probe3_lean/` |
| Modal adapter (source of modal_lora preds) | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/modal_larger_1ep_2026_08_09/` |
| Unanimous infer job | (fill after run) |
| Unanimous preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora/` |
| Results | `experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md` |
