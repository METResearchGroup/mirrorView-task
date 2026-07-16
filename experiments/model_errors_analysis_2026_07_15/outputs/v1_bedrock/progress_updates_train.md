# V1.3A Logistic training — progress updates

## 2026-07-15 start

- Branch: `model-errors-long-csv-2026-07-15`
- Task: V1.3A balanced logistic regression on shared split (predict `is_error`)
- Constraints: load existing `split_ids.json` only (no re-split); features `only_original`; **no Bedrock**
- Prepared inputs present:
  - `X_only_original.npy` (8791, 256)
  - `analysis_meta.csv` / `analysis_with_split.csv`
  - `split_ids.json` (train=7032, test=1759, seed=42)
- Next: implement `analyze/v1_linear_separator.py`, fit, write metrics/artifacts under `outputs/v1_bedrock/`
## 2026-07-16 02:05:51 UTC — data load

- Loading shared split from `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/split_ids.json` (no re-split)
- Features: `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/X_only_original.npy` + `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/analysis_meta.csv`

## 2026-07-16 02:05:51 UTC — data loaded

- n_train=7032 n_test=1759 seed=42
- is_error rates: train=0.3585 test=0.3587
- X shape=[8791, 256] feature_set=`only_original`

## 2026-07-16 02:05:51 UTC — train done

- Fit `StandardScaler` + `LogisticRegression(class_weight='balanced')` on train only
- Model artifact pending write to `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/linear_separator_model.joblib`

## 2026-07-16 02:05:51 UTC — metrics

- **Test** accuracy=0.5713 roc_auc=0.5995 pr_auc=0.4308 precision_error=0.4276 recall_error=0.5753 f1_error=0.4905
- **Train** accuracy=0.6027 roc_auc=0.6543 pr_auc=0.4884
- Confusion (test, error=1): tn=642 fp=486 fn=268 tp=363

## 2026-07-16 02:05:51 UTC — artifact paths

- `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/linear_separator_metrics.json`
- `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/logistic_metrics.json` (alias)
- `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/linear_separator_model.joblib`
- `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/linear_separator_coefficients.csv`
- `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/linear_separator_predictions.csv`
- Progress: `/Users/mark/.cursor/worktrees/mirrorView-task/47kw/experiments/model_errors_analysis_2026_07_15/outputs/v1_bedrock/progress_updates_train.md`

- Status: **complete** (no Bedrock calls; used existing shared split only)

