# Step 4: Test response time against ambiguity scores

## Goal

Ask whether posts scored as ambiguous are decided more slowly after controlling for reading length, trial order, and rater identity. Report minority-voter and tie contrasts as supporting checks.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e3_response_time.py
```

Flow: join trial frame to E1 and E2 post scores, drop non-positive response times, fit an ordinary least squares model of log response time on ambiguity score, character count, trial index, and rater fixed effects via demeaning within rater, write coefficient tables and contrast summaries.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E3 contract |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv` | Trials |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/post_scores.csv` | E1 scores |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/post_effects.csv` | E2 scores |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e3_response_time.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e3/model_summary.json`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e3/contrasts.csv`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/**`

## Contracts to freeze

### Primary model

Dependent variable: `log(response_time_ms)`.

Predictors after within-rater demeaning of all variables: `ambiguity_score` from E1, `adjusted_ambiguity_score` from E2 (fit two separate models), `char_count`, `trial_index`.

Report slope of the ambiguity predictor and residual variance for each model.

### Contrasts in `contrasts.csv`

Rows:

1. Mean log response time for minority voters versus majority voters on non-tie split posts.
2. Mean log response time on tie posts versus unanimous posts.
3. Mean log response time on the top quartile of E2 adjusted ambiguity versus the bottom quartile.

Columns: `contrast_name`, `group_a`, `group_b`, `mean_log_rt_a`, `mean_log_rt_b`, `diff_a_minus_b`, `n_a`, `n_b`.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e3_response_time.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
summary = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e3/model_summary.json").read_text())
contrasts = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e3/contrasts.csv")
assert "e1_ambiguity_slope" in summary
assert "e2_ambiguity_slope" in summary
assert len(contrasts) >= 3
print("e3_ok", round(summary["e1_ambiguity_slope"], 5), len(contrasts))
PY
```

Expected shape:

```text
e3_ok <slope> 3
```

## Pass / fail

Pass: both slopes present, three contrasts written, only positive response times used.

Fail: missing joins, zero or negative times kept, fewer than three contrasts.

## Commit gate

Commit E3 script and outputs after `e3_ok` prints.
