# Step 7: Experiment 4: run the zero-shot baseline, score all predictions, and write RESULTS.md

Notation: `P` = `/workspace/experiments/finetune_qwen_model_2026_08_08/`.

## Scope

- **Caller:** `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py` `main`
- **Task:** Run zero-shot baseline inference on both balanced union test sets (`part3_zeroshot_001`). Score predictions from Experiments 1 to 3 (Steps 4 to 6) and the zero-shot baseline. Add remove-F1 95% bootstrap CIs over test posts. Write `cross_eval.csv` and `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md`.
- **Out of scope:** Retraining adapters, changing label builders or splits, editing Part 2 `RESULTS.md`, adding new experiments, changing `P/evaluate.py`.

## Dependencies

Steps 4 to 6 wrote prediction CSVs (local or S3) for all three fine-tuned arms on both test sets:

```text
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/test_unanimous.csv
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment1_unanimous/preds/test_modal.csv
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/test_unanimous.csv
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment2_modal/preds/test_modal.csv
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/test_unanimous.csv
/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment3_modal_size_matched/preds/test_modal.csv
```

Step 3 added `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py` with `--mode infer_baseline`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md` | Decisions and pool table; run ids, metric rules |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | `score_prediction_csv`, `effective_pred_labels`, `compute_metrics` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` | Prediction CSV columns written by inference |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md` | Four-decimal metric table style |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` | Part 2 modal reference table style |
| `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/shared/run_config.py` | `MODEL_ID`, `RANDOM_SEED`, `S3_PREFIX` |
| `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/data/split_manifest.csv` | Split counts for RESULTS.md |
| `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py` | `infer_baseline` CLI for Experiment 4 |
| `/workspace/AGENTS.md` | `RESULTS.md` format: tables and short statements |

## Files allowed to change

- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/preds/test_unanimous.csv` (written by baseline infer job)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/preds/test_modal.csv` (written by baseline infer job)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/scores/cross_eval.csv` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/test_score_all.py` (new)
- `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md` (new)

## Files forbidden to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md`
- Prediction CSVs under `experiment1_unanimous/preds/`, `experiment2_modal/preds/`, `experiment3_modal_size_matched/preds/`
- `/workspace/shared/data/**`
- `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md`
- Adapter weights on S3 or locally

## Public contracts

Import and reuse from `P/evaluate.py`: `score_prediction_csv`, `effective_pred_labels`, `compute_metrics`. Do not copy scoring logic.

`bootstrap_f1_ci(y_true, y_pred, n_resamples=1000, seed=1) -> tuple[float, float, float]` resamples test posts with replacement, computes remove-F1 per resample via `compute_metrics`, and returns point F1 with 95% percentile bounds (`f1_ci_low`, `f1_ci_high`) at the 2.5th and 97.5th percentiles.

`invalid_rate(frame) -> float` counts rows where `predicted_decision == "__invalid__"` (from `P/src/parse_prediction.INVALID_DECISION`) or `predicted_label` is NA or empty, over row count.

`score_arm_test_set(pred_path: Path, arm: str, test_set: str) -> dict` reads the CSV and calls `score_prediction_csv` for accuracy, precision, recall, and f1; builds `y_true` and effective `y_pred` via `effective_pred_labels` for bootstrap; adds `n`, `n_remove` (gold remove count), `invalid_rate`, and CI fields.

`ARM_PRED_PATHS` maps four arms to two pred files:

| arm | unanimous test | modal test |
| --- | --- | --- |
| `zero-shot` | `experiment4_cross_eval/preds/test_unanimous.csv` | `experiment4_cross_eval/preds/test_modal.csv` |
| `experiment1_unanimous` | `experiment1_unanimous/preds/test_unanimous.csv` | `experiment1_unanimous/preds/test_modal.csv` |
| `experiment2_modal` | `experiment2_modal/preds/test_unanimous.csv` | `experiment2_modal/preds/test_modal.csv` |
| `experiment3_modal_size_matched` | `experiment3_modal_size_matched/preds/test_unanimous.csv` | `experiment3_modal_size_matched/preds/test_modal.csv` |

`write_cross_eval_csv(path, rows)` writes eight rows with columns:

| Column | Meaning |
| --- | --- |
| `arm` | `zero-shot`, `experiment1_unanimous`, `experiment2_modal`, or `experiment3_modal_size_matched` |
| `test_set` | `test_unanimous` or `test_modal` |
| `n` | Row count |
| `n_remove` | Gold remove count |
| `accuracy` | From `compute_metrics` |
| `precision` | Positive class remove |
| `recall` | Positive class remove |
| `f1` | Remove-F1 point estimate |
| `f1_ci_low` | Bootstrap 2.5th percentile |
| `f1_ci_high` | Bootstrap 97.5th percentile |
| `invalid_rate` | Fraction invalid generations |

Prediction CSVs must include `keep_remove_label`, `predicted_decision`, and `predicted_label`, plus `message_id`, `decision`, and `raw_generation` from `P/inference.py`. Invalid rows count as wrong through `effective_pred_labels`.

### RESULTS.md

Write `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md` from `cross_eval.csv` and `split_manifest.csv` counts.

The file must include:

1. Title, model `Qwen/Qwen3.5-4B`, seed 1, positive class remove.
2. **4 by 2 remove-F1 matrix with 95% CIs.** Rows: zero-shot, Experiment 1, Experiment 2, Experiment 3. Columns: unanimous test, modal test. Cell format: `0.XXXX [0.XXXX, 0.XXXX]` (four decimals, same as Part 2 tables).
3. **Full metrics table** copied from `cross_eval.csv` (all columns above).
4. **Split counts table** from `data/split_manifest.csv`: modal pool posts, unanimous-min3 posts, balanced train rows per experiment, balanced test rows per test set (`n`, `n_remove`, `n_keep`).
5. **One plain paragraph** on what the union experiment numbers show (best F1 cell; invalid rates if nonzero). No causal claims or head-to-head claims against Part 2-only baselines.
6. **Part 2 reference block** labeled `Part 2 reference (different base model: Qwen/Qwen3-4B-Instruct-2507)`. Copy test remove-F1 only from `P/RESULTS.md` (unanimous 0.7407 baseline, 0.9688 fine-tuned) and `larger_finetune` `RESULTS.md` (modal 0.7210 baseline, 0.6962 fine-tuned). Note they are not comparable to this union experiment.

## Pytest files

### `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/test_score_all.py`

Class `TestBootstrapF1Ci`, `TestInvalidRate`, `TestScoreArmTestSet`, `TestMissingPreds`.

```text
given y_true [1, 0, 1, 0] and y_pred [1, 0, 0, 1]
when bootstrap_f1_ci with seed 1 and n_resamples 1000
then f1_ci_low <= point f1 <= f1_ci_high

given the same inputs and seed 1
when bootstrap_f1_ci is called twice
then f1, f1_ci_low, and f1_ci_high are identical

given a frame with one __invalid__ row and gold remove
when effective_pred_labels and compute_metrics run
then that row counts as wrong (not as a correct remove)

given invalid_rate on a frame with 2 invalid rows out of 10
when invalid_rate
then result is 0.2

given a missing pred path
when score_arm_test_set
then FileNotFoundError is raised with the path in the message
```

Tests use synthetic CSV fixtures under `tmp_path`. No SageMaker calls. No S3 downloads.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode infer_baseline --experiment experiment4_cross_eval \
  --run-id part3_zeroshot_001 --wait

aws s3 sync \
  s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/preds/ \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py \
  --write-results /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md

PYTHONPATH=. uv run pytest \
  /workspace/experiments/finetune_lora_phase2_part3_2026_09_24/tests/test_score_all.py -q
```

Expected: SageMaker job completes; both baseline pred CSVs exist locally; `cross_eval.csv` has eight rows; `RESULTS.md` has the 4 by 2 matrix, full metrics table, split counts, one plain paragraph, and Part 2 reference block; pytest exits 0.

## Must pass

- `score_all.py` imports `score_prediction_csv`, `effective_pred_labels`, `compute_metrics` from `P/evaluate.py`.
- Bootstrap uses 1000 resamples, seed 1, percentile method over test posts.
- All eight arm by test-set combinations are scored.
- `RESULTS.md` matches the contract above.
- Part 2 numbers appear only in the labeled reference block.

## Must fail

- Reimplementing metric math instead of importing `P/evaluate.py`.
- Editing fine-tuned prediction CSVs from Steps 4 to 6.
- Claiming this union experiment beats Part 2-only baselines (different base model and data).
- Writing F1 without CIs on the 4 by 2 matrix.
- Silent skip when a pred file is missing.

## Implement-from-spec notes

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md`. Full auto. Do not pause after contracts.

Phase 1 names `score_all.py` `main` as the caller.

Phase 2 scaffolds `score_all.py` and imports from `P/evaluate.py`.

Phase 3 locks `bootstrap_f1_ci`, `invalid_rate`, `score_arm_test_set`, `ARM_PRED_PATHS`, and `cross_eval.csv` columns.

Phase 4 writes `test_score_all.py` with the cases above.

Phase 5 implements `bootstrap_f1_ci`, then `invalid_rate`, then `score_arm_test_set`, then `write_cross_eval_csv` and `RESULTS.md` rendering, then `main`.

Phase 6 completes when baseline preds exist, `cross_eval.csv` and `RESULTS.md` are written, and pytest exits 0.
