# Step 2: Run Analysis 1 on original text

## Goal

Compute the locked surface metrics and classifiers on each cohort post's original text, summarize them by cell, and write tables under the experiment outputs tree.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py
```

Flow: load `four_cell_cohort.csv`, compute deterministic metrics for every row, run valence and intergroup and PRIME classifiers on original text, write a per post feature CSV, write a per cell summary CSV, print a short summary.

In scope: Analysis 1 scripts and outputs only.

Out of scope: Stage 1 language model feature generation, word clouds, stance tables, README or RESULTS rewrites.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` | Locked Analysis 1 feature list |
| `/Users/mark/src/work/mirrorview-wt/shared/textual_features/registry.py` | Metric and classifier registry names |
| `/Users/mark/src/work/mirrorview-wt/shared/textual_features/valence.py` | `is_positive` classifier |
| `/Users/mark/src/work/mirrorview-wt/shared/textual_features/intergroup.py` | `is_intergroup` classifier |
| `/Users/mark/src/work/mirrorview-wt/shared/textual_features/prime.py` | `is_prime` binary any of classifier |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/steps/step1.md` | Cohort path and columns |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/per_post_features.csv` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/cell_summary.csv` (create or regenerate)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/textual_features/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv` (read only here)
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`

## Contracts to freeze

### Input

Read `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv`.

Require columns `message_id`, `original_text`, `cell`, `sample_toxicity_type`.

### Text surface

All Analysis 1 metrics and classifiers run on `original_text` only.

### Deterministic metrics

Use `shared.textual_features.registry.get_feature` with these registry names, and write the metric column names returned by each metric object:

| Registry name | Purpose |
|---------------|---------|
| `CHAR_COUNT` | character count |
| `WORD_COUNT` | word count |
| `SENTENCE_COUNT` | sentence count |
| `AVG_SENTENCE_LENGTH` | average sentence length |
| `PUNCTUATION_DENSITY` | punctuation density |
| `FLESCH_KINCAID_GRADE` | Flesch Kincaid grade |
| `READING_EASE` | Flesch reading ease |

Do not require `PUNCTUATION_COUNT` in the summary, because the grill list asks for punctuation density.

### Classifiers

Call the existing single post classifiers on `original_text`:

| Module | Output field to store |
|--------|------------------------|
| `shared.textual_features.valence.classify_post` | `is_positive` |
| `shared.textual_features.intergroup.classify_post` | `is_intergroup` |
| `shared.textual_features.prime.classify_post` | `is_prime` |

The shared PRIME classifier is a single binary any of label. It does not emit separate prestige, in group, moral, and emotional flags. Store `is_prime` only. Do not invent four separate PRIME models in this step.

Classifiers need `OPENAI_API_KEY` from the repo root `.env` through the existing env loader.

### Per post output

Path: `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/per_post_features.csv`

Must include `message_id`, `cell`, `sample_toxicity_type`, every deterministic metric column above, `is_positive`, `is_intergroup`, and `is_prime`.

Row count must equal the cohort row count (3718 on current data).

### Per cell summary

Path: `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/cell_summary.csv`

One row per `cell`. For each continuous metric, write the median. For each binary classifier, write the mean as a proportion. Also write:

- `n` as the cell size
- `pct_high_toxicity` as the share of rows with `sample_toxicity_type == sample_high_toxicity`

Order rows as `unanimous_keep`, `majority_keep`, `majority_remove`, `unanimous_remove`.

### Descriptive only

Do not compute p values, confidence intervals, or trend tests.

## Exact commands

### 1. Smoke metrics on three posts without classifiers

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
from shared.textual_features.registry import (
    CHAR_COUNT,
    get_feature,
)

cohort = pd.read_csv(
    "experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv"
)
metric = get_feature(CHAR_COUNT).build()
vals = [metric.calculate(t) for t in cohort["original_text"].head(3)]
print({"n_cohort": len(cohort), "char_sample": vals})
PY
```

Expected: `n_cohort` is 3718 after Step 1, and `char_sample` is a list of three numbers.

### 2. Full Analysis 1 run

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py
```

Expected:

- `outputs/analysis1/per_post_features.csv` has 3718 rows
- `outputs/analysis1/cell_summary.csv` has 4 rows
- printed medians for character count decline across the ordered cells in the same direction as the grill note (unanimous keep longest, unanimous remove shortest), or the script prints the four medians for manual check

### 3. Summary shape check

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
summary = pd.read_csv(
    "experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/cell_summary.csv"
)
assert list(summary["cell"]) == [
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
]
assert len(summary) == 4
needed = {"n", "pct_high_toxicity", "is_positive", "is_intergroup", "is_prime"}
missing = needed - set(summary.columns)
assert not missing, missing
print("analysis1_summary_ok", summary[["cell", "n", "pct_high_toxicity"]].to_dict("records"))
PY
```

Expected stdout starts with `analysis1_summary_ok` and shows n values 1490, 1480, 594, 154.

## Pass / fail

Pass:

- Per post CSV row count matches the cohort.
- Cell summary has four ordered rows and the required columns.
- Metrics use original text only.
- PRIME is stored as `is_prime` only.

Fail:

- Classifiers run on mirror text.
- Separate prestige or moral columns are invented without new shared classifiers.
- Statistical tests appear in the script output.

## Commit gate

Commit Analysis 1 scripts and CSVs after the summary shape check passes. Classifier labels may vary slightly across model calls, so do not freeze exact valence proportions in this plan.
