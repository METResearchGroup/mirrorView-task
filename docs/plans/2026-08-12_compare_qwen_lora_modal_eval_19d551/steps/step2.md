# Step 2: Wire three-arm evaluate and pred sync

## Goal

Implement local evaluation that scores three prediction arms into `RESULTS.md`, and a sync script that copies existing baseline and modal prediction CSVs from S3 into the local preds layout. Reuse metric helpers from `experiments/finetune_qwen_model_2026_08_08/evaluate.py` (`score_prediction_csv`, `format_metric`, and related helpers). Do not submit SageMaker in this step.

## Caller / unit of work

1. `sync_existing_preds.py` downloads four CSVs into `preds/baseline/` and `preds/modal_lora/`.
2. `evaluate.py` reads six CSVs under `preds/{baseline,unanimous_lora,modal_lora}/` and writes `RESULTS.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | Helpers to import; do not fork metric math |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py` | Thin-wrapper pattern |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/s3_upload.py` | S3 URI parsing pattern if useful for download |
| `/workspace/docs/plans/2026-08-12_compare_qwen_lora_modal_eval_19d551/steps/step1.md` | Frozen arm names and paths |

## Files allowed to change

- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/tests/test_evaluate_three_arms.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/tests/__init__.py`

## Files forbidden to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` behavior used by prior RESULTS (do not break the two-arm API)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/**`
- `/workspace/shared/**`

## Contracts

### Arm directory names (exact)

| Arm display name | Local directory under `preds/` | S3 source for sync |
|------------------|--------------------------------|--------------------|
| baseline | `baseline` | `.../preds/baseline/{train,test}_labels.csv` |
| unanimous_lora | `unanimous_lora` | produced in Step 3 and 4, not by sync |
| modal_lora | `modal_lora` | `.../preds/fine_tuned/{train,test}_labels.csv` |

### `sync_existing_preds.py`

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds
```

Must download the four existing CSVs into:

- `preds/baseline/train_labels.csv`
- `preds/baseline/test_labels.csv`
- `preds/modal_lora/train_labels.csv`
- `preds/modal_lora/test_labels.csv`

Refuse to overwrite unless `--force` is set.

### `evaluate.py`

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --write-results experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
```

`RESULTS.md` must include:

- Model id `Qwen/Qwen3-4B-Instruct-2507`
- Data line naming the modal registry source and the larger-experiment frozen splits
- Positive class = remove
- Train table and Test table with columns: Arm, Accuracy, Precision, Recall, F1
- Rows in order: `baseline`, `unanimous_lora`, `modal_lora`

Missing `unanimous_lora` CSVs must raise `FileNotFoundError` with the missing path. Do not silently drop an arm.

### Tests

`tests/test_evaluate_three_arms.py` must:

1. Build a temporary preds tree with six tiny valid CSVs.
2. Assert `evaluate_preds_dir` returns metrics for all three arms on train and test.
3. Assert rendered markdown contains the three arm names in order.

## Pass / fail

Pass:

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/tests/test_evaluate_three_arms.py -q
```

Expected: all tests pass.

Fail if evaluate still hardcodes only `baseline` and `fine-tuned`, or if sync writes into `fine_tuned/` instead of `modal_lora/`.

## Out of scope

SageMaker launch, IAM, Docker, downloading the unanimous adapter.
