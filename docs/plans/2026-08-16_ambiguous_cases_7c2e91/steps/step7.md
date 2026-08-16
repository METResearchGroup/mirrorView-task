# Step 7: Measure model difficulty and abstention value

## Goal

Join existing Qwen3 Next 80B correctness labels to human vote margins and ambiguity scores, then compare abstention policies that drop the most ambiguous posts under each score definition.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e6_model_difficulty.py
```

Flow: load `experiments/model_errors_analysis_2026_07_15/outputs/base_model_llm_labels.csv`, join to post frame, E1 scores, and E2 scores, tabulate error rate by minority-share band and by ambiguity quartile, build accuracy-versus-coverage curves when abstaining on the top 10%, 20%, 30%, and 50% most ambiguous posts under raw minority share, E1 ambiguity, and E2 adjusted ambiguity, write tables and summary JSON. Do not call any model API.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E6 contract |
| `/workspace/experiments/model_errors_analysis_2026_07_15/outputs/base_model_llm_labels.csv` | Correctness labels |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/post_scores.csv` | E1 scores |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/post_effects.csv` | E2 scores |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e6_model_difficulty.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e6/error_by_band.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e6/abstention_curves.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e6/summary.json`

## Files forbidden to change

- `/workspace/experiments/model_errors_analysis_2026_07_15/**`
- `/workspace/shared/**`

## Contracts to freeze

### Join key

`post_id` in the correctness file equals `post_id` in the post frame. Restrict the abstention analysis to the 3993 posts with three or more raters that join successfully.

### Error-by-band table

Bands: `unanimous` (`minority_share == 0`), `lopsided` (`0 < minority_share <= 0.25`), `close` (`minority_share > 0.25`). Columns: `band`, `n`, `error_rate`.

### Abstention curves

For each score in `{minority_share, ambiguity_score, adjusted_ambiguity_score}` and each abstain fraction in `{0.0, 0.1, 0.2, 0.3, 0.5}`, keep the lowest-ambiguity coverage fraction of posts and compute accuracy of the existing model predictions against the modal human label (`remove_count > keep_count`, ties excluded from accuracy). Columns: `score_name`, `abstain_fraction`, `coverage`, `n_evaluated`, `accuracy`.

### Summary keys

`base_accuracy_ge3_nontie`, `best_score_at_30pct_abstain`, `best_accuracy_at_30pct_abstain`, `error_rate_unanimous`, `error_rate_close`.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e6_model_difficulty.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
summary = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e6/summary.json").read_text())
curves = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e6/abstention_curves.csv")
assert "best_score_at_30pct_abstain" in summary
assert len(curves) >= 15
print("e6_ok", round(summary["base_accuracy_ge3_nontie"], 4), summary["best_score_at_30pct_abstain"])
PY
```

Expected shape:

```text
e6_ok <acc> <score_name>
```

## Pass / fail

Pass: error-by-band and abstention tables written, no API calls, join coverage equals 3993 or is reported if lower.

Fail: regenerated model labels, missing abstention rows, silent join loss without a count in the summary.

## Commit gate

Commit E6 script and outputs after `e6_ok` prints.
