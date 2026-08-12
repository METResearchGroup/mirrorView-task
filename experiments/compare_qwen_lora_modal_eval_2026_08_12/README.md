# Compare three Qwen keep/remove arms on one modal-label eval set

Pull requests 54 and 57 each trained a LoRA adapter, but each reported metrics on a different labeled set. This experiment scores three arms on the same frozen modal keep/remove splits:

1. `baseline`: base `Qwen/Qwen3-4B-Instruct-2507` with no LoRA
2. `unanimous_lora`: adapter from pull request 54 (`passrole_probe3`), trained on unanimous min-3 labels
3. `modal_lora`: adapter from pull request 57 (`modal_larger_1ep_2026_08_09`), trained on modal labels

No retraining happens here. Evaluation reuses the frozen chat files from `experiments/larger_finetune_qwen_model_2026_08_08/data/`, which come from registry entry `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`.

## Design freeze

| Topic | Value |
|-------|-------|
| Goal | Compare three keep/remove arms on one modal-label eval set |
| Arms | `baseline` (no LoRA), `unanimous_lora` (pull request 54 adapter `passrole_probe3`), `modal_lora` (pull request 57 adapter `modal_larger_1ep_2026_08_09`) |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Eval data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via frozen files in `experiments/larger_finetune_qwen_model_2026_08_08/data/` |
| Eval rows | Same balanced 1:1 modal splits as the larger experiment: train 4500 / test 1126; seed 1 |
| No train | Do not retrain adapters |
| Pred layout | `preds/{baseline,unanimous_lora,modal_lora}/{train,test}_labels.csv` |
| Metrics | Accuracy, precision, recall, F1; positive class = remove |
| Remote image | Reuse ECR `mirrorview-larger_finetune_qwen_model_2026_08_08:latest` |
| Unanimous adapter S3 | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/adapters/passrole_probe3/` |
| Modal data S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/` |
| Existing preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/{baseline,fine_tuned}/` |
| New preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora/` |
| Deps | `uv sync --extra finetune-qwen-2026-08-08` |

## Install

```bash
uv sync --extra finetune-qwen-2026-08-08
```

## 1. Sync existing baseline and modal preds

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --force
```

## 2. Infer the unanimous adapter on the modal splits

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --wait
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

Filled in Step 4 after the remote infer job completes.
