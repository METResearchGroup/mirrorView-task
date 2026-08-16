# Step 2: Fit the beta-binomial noise floor and continuous scores

## Goal

Fit a beta-binomial model on per-post remove counts from the post frame, write continuous ambiguity scores for every post with three or more raters, validate with a high-rater half-split check, and estimate how often the old four-cell labels are contaminated by sampling noise.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e1_beta_binomial.py
```

Flow: load post frame and trial frame, fit beta-binomial population parameters by maximum likelihood, write per-post posterior mean remove probability and middle-band probability, run half-split correlation on posts with six or more raters, simulate four-cell assignment under the fitted model, write summary JSON.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E1 contract |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/post_frame.csv` | Inputs |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv` | Half-split inputs |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e1_beta_binomial.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/src/beta_binomial.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/post_scores.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/summary.json`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/**`

## Contracts to freeze

### Model

Each post has true remove probability `p` drawn from `Beta(alpha, beta)`. Observed removes given `n_raters` are `Binomial(n_raters, p)`. Fit `alpha` and `beta` by maximizing the beta-binomial likelihood on the post frame.

Middle band is fixed as `p` in `[0.25, 0.75]`. Ambiguity score for a post is the posterior probability that `p` lies in that band, given the observed counts and the fitted prior.

### Output columns for `post_scores.csv`

| Column | Meaning |
|--------|---------|
| `post_id` | message id |
| `n_raters` | integer |
| `remove_count` | integer |
| `remove_share` | empirical share |
| `alpha_hat` | fitted prior alpha (repeated) |
| `beta_hat` | fitted prior beta (repeated) |
| `posterior_mean_p` | posterior mean of `p` |
| `ambiguity_score` | posterior Prob(`p` in `[0.25, 0.75]`) |
| `four_cell_label` | `unanimous_keep`, `majority_keep`, `majority_remove`, `unanimous_remove`, or `tie` |

### Summary JSON required keys

| Key | Meaning |
|-----|---------|
| `alpha_hat` | float |
| `beta_hat` | float |
| `n_posts` | 3993 |
| `half_split_pearson_r` | correlation of remove shares across random halves on posts with `n_raters >= 6` |
| `half_split_n_posts` | integer |
| `contamination_majority_keep_at_3` | simulated share of majority-keep assignments at 3 raters whose true `p` is below 0.25 |
| `seed` | 42 |

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e1_beta_binomial.py
```

Expected: prints `alpha_hat`, `beta_hat`, `half_split_pearson_r`, and writes both output files with 3993 score rows.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
scores = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e1/post_scores.csv")
summary = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e1/summary.json").read_text())
assert len(scores) == 3993
assert scores["ambiguity_score"].between(0, 1).all()
assert "half_split_pearson_r" in summary
print("e1_ok", len(scores), round(summary["alpha_hat"], 4), round(summary["beta_hat"], 4))
PY
```

Expected shape:

```text
e1_ok 3993 <alpha> <beta>
```

## Pass / fail

Pass: 3993 scored posts, scores in `[0, 1]`, summary contains half-split and contamination keys.

Fail: missing ties, scores outside `[0, 1]`, half-split skipped.

## Commit gate

Commit E1 modules and outputs after the check prints `e1_ok`.
