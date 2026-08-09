# Step 5: Implement local evaluation and RESULTS.md writer

## Goal

Implement `experiments/finetune_qwen_model_2026_08_08/evaluate.py` to score baseline vs fine-tuned prediction CSVs on train and test, treating `__invalid__` as never correct, and write `RESULTS.md` with two tables.

## Caller / unit of work

**Main caller:** `evaluate.py` CLI (local only; not a SageMaker mode).

```text
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/finetune_qwen_model_2026_08_08/RESULTS.md
```

Expected local layout (after sync from S3 or local smoke):

```text
preds/
  baseline/train_labels.csv
  baseline/test_labels.csv
  fine_tuned/train_labels.csv
  fine_tuned/test_labels.csv
```

Happy path:

1. Load four CSVs.
2. For each row: if `predicted_decision == __invalid__` or `predicted_label` is NA, treat prediction as wrong vs gold for metrics (never equal to gold for scoring). Concrete rule: set effective `y_pred = 1 - y_true` **only inside metric computation**, without rewriting the CSV.
3. Compute accuracy, precision, recall, F1 with **positive class = remove (`1`)**.
4. Write `RESULTS.md` with provenance + train table + test table (rows: baseline, fine-tuned).

**Out of scope:** running inference; SageMaker; changing pred CSV schema; numeric pass/fail on F1.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Metrics helpers + RESULTS markdown shape precedent |
| `/workspace/docs/plans/2026-08-08_finetune_qwen3_4b_lora_4403cd/steps/step4.md` | Pred CSV + invalid contract |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_evaluate_metrics.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (evaluate command)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md` only when intentionally writing from the script (may be absent until Step 8)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_*/**` (import metrics math by copy or reimplement; **do not** edit v1/v2)
- Pred generation code beyond read-only

## Contracts to freeze

### Metrics

| Metric | Definition |
|--------|------------|
| Positive class | remove (`keep_remove_label=1`) |
| Invalid handling | never counts as correct; effective pred flipped vs gold only for scoring |
| Reported floats | 4 decimal places in markdown (match prompt-eng style) |

### RESULTS.md shape

```markdown
# Qwen3-4B LoRA fine-tune keep/remove results

- Model: `Qwen/Qwen3-4B-Instruct-2507`
- Data: unanimous min-3 balanced n=308; seed=1; 80/20
- Positive class: remove
- Exploratory teachability run (no numeric success bar)

## Train

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | ... | ... | ... | ... |
| fine-tuned | ... | ... | ... | ... |

## Test

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | ... | ... | ... | ... |
| fine-tuned | ... | ... | ... | ... |
```

## Exact commands

```bash
cd /workspace

# Unit tests with synthetic tiny CSVs (invalid row must reduce accuracy):
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/finetune_qwen_model_2026_08_08/tests/test_evaluate_metrics.py -q

# After four real/smoke CSVs exist:
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/finetune_qwen_model_2026_08_08/RESULTS.md
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Invalid scoring | Invalid never increases correct count | Invalid treated as correct or dropped silently |
| Tables | Train + test; baseline + fine-tuned rows | Single table / wrong arms |
| Positive class | remove | keep-as-positive |
| Missing file | Non-zero exit with clear path error | Traceback-only |

## Done when

1. `evaluate.py` implements frozen metrics + RESULTS writer.
2. Unit tests cover invalid-as-wrong.
3. No remote jobs required for this step’s gate.
