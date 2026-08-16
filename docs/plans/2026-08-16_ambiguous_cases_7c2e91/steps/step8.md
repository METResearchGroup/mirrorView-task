# Step 8: Export the close-reading sample and freeze README and RESULTS

## Goal

Export stratified sample posts for qualitative reading, then write the experiment README and RESULTS documents that cover E1 through E7.

## Caller / unit of work

Main callers:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e7_close_reading_sample.py
```

Then edit:

- `/workspace/experiments/ambiguous_cases_2026_08_16/README.md`
- `/workspace/experiments/ambiguous_cases_2026_08_16/RESULTS.md`

Flow: export three strata of posts with text and scores, write the sample CSV, then document run commands and the quantitative findings from prior steps without inventing unread qualitative conclusions.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E7 strata |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/README.md` | README tone |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/RESULTS.md` | RESULTS tone |
| All `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/**/summary.json` files | Numbers to report |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e7_close_reading_sample.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e7/close_reading_sample.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e7/summary.json`
- `/workspace/experiments/ambiguous_cases_2026_08_16/README.md`
- `/workspace/experiments/ambiguous_cases_2026_08_16/RESULTS.md`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md`
- Prior experiment output trees outside this folder

## Contracts to freeze

### Sample strata

| `stratum` | Rule | Target n |
|-----------|------|----------|
| `tie` | `is_tie` true | up to 40 |
| `high_ambiguity_multi_rater` | `n_raters >= 6` and top adjusted ambiguity among those posts | up to 40 |
| `reclassified_unanimous` | unanimous at 3 raters with E1 `ambiguity_score` above the median of all posts | up to 40 |

Sampling seed is 42. Columns: `stratum`, `post_id`, `original_text`, `n_raters`, `keep_count`, `remove_count`, `ambiguity_score`, `adjusted_ambiguity_score`, `sample_toxicity_type`, `sampled_stance`.

### README requirements

State the goal, point to `PROPOSAL.md`, list exact run commands for Steps 1 through 8 in order, and name the output paths.

### RESULTS requirements

Report the quantitative findings from E1 through E6 with numbers copied from the summary JSON files. For E7, report only that the sample was exported and how many rows per stratum. Do not invent close-reading conclusions that were not actually read and coded.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e7_close_reading_sample.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
sample = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e7/close_reading_sample.csv")
assert set(sample["stratum"]) <= {"tie", "high_ambiguity_multi_rater", "reclassified_unanimous"}
assert sample["post_id"].nunique() == len(sample)
print("e7_ok", sample["stratum"].value_counts().to_dict())
PY
```

Expected shape:

```text
e7_ok {'tie': ..., 'high_ambiguity_multi_rater': ..., 'reclassified_unanimous': ...}
```

## Pass / fail

Pass: sample CSV exists with three strata, README has run commands, RESULTS cites summary numbers from E1 through E6 and does not invent unread qualitative claims.

Fail: empty sample, README missing commands, RESULTS invents close-reading themes.

## Commit gate

Commit E7 script, sample CSV, README, and RESULTS after `e7_ok` prints and both markdown files are written.
