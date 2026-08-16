# Step 3: Fit rater severity and post removability

## Goal

Fit a crossed logistic model where the log-odds that rater `j` removes post `i` is a post effect plus a rater effect. Write adjusted post ambiguity scores after removing rater severity, report variance shares, and run a party-by-stance interaction check.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e2_rater_effects.py
```

Flow: load trial and post frames restricted to posts in the post frame, fit alternating or joint logistic post and rater fixed effects with L2 regularization, write post effects and rater severity, compute adjusted remove probabilities at mean rater severity, write adjusted ambiguity as distance of adjusted probability from 0 or 1 toward the middle, report variance of post effects versus rater effects, fit an additive party-by-stance term and report its coefficient.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E2 contract |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv` | Inputs |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/post_scores.csv` | Join target |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e2_rater_effects.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/post_effects.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/rater_effects.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/summary.json`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e1/**`

## Contracts to freeze

### Model

Use scikit-learn `LogisticRegression` on a sparse design with one column per post, one column per rater, no intercept, and L2 penalty `C=1.0`. Target is `is_remove`. Fit only on trials whose `post_id` appears in the post frame.

Adjusted remove probability for a post is the sigmoid of the post coefficient evaluated at rater effect 0 (mean-centered rater effects). Adjusted ambiguity score is `1 - 2 * abs(adjusted_p - 0.5)`, so 1 is fully middle and 0 is fully extreme.

### Party-by-stance check

Among trials where `party_group` is `democrat` or `republican` and `sampled_stance` is present, fit the same model with one extra binary feature that is 1 when the rater's party mismatches the post stance under the mapping democrat-left and republican-right as match. Report the coefficient and note that the study design predicts a coefficient near zero.

### Output files

`post_effects.csv` columns: `post_id`, `post_effect`, `adjusted_p`, `adjusted_ambiguity_score`.

`rater_effects.csv` columns: `participant_id`, `rater_effect`, `n_trials`, `empirical_remove_rate`.

`summary.json` keys: `var_post_effects`, `var_rater_effects`, `share_var_post`, `share_var_rater`, `party_stance_mismatch_coef`, `n_trials_fit`, `n_posts`, `n_raters`, `seed`.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e2_rater_effects.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
posts = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e2/post_effects.csv")
raters = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e2/rater_effects.csv")
summary = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e2/summary.json").read_text())
assert len(posts) == 3993
assert posts["adjusted_ambiguity_score"].between(0, 1).all()
assert "share_var_post" in summary
print("e2_ok", len(posts), len(raters), round(summary["share_var_post"], 3))
PY
```

Expected shape:

```text
e2_ok 3993 <n_raters> <share>
```

## Pass / fail

Pass: 3993 post effects, adjusted scores in `[0, 1]`, summary has variance shares and the party-stance coefficient.

Fail: posts outside the post frame included, missing rater effects, no summary.

## Commit gate

Commit E2 script and outputs after `e2_ok` prints.
