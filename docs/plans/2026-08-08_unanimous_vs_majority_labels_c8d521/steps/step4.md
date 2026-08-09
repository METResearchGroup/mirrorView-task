# Step 4: Run Analysis 3 stance tables within each toxicity stratum

## Goal

Build three left or right by cell tables from the cohort, one table for each toxicity stratum, and write them under the experiment outputs tree.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py
```

Flow: load the cohort, split by `sample_toxicity_type`, count `sampled_stance` by `cell` inside each stratum, write three CSV tables plus one combined CSV, print the tables.

In scope: Analysis 3 script and outputs.

Out of scope: participant politics fields from results full, statistical tests, README or RESULTS rewrites.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` | Three table stance design |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/steps/step1.md` | Cohort columns |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Confirms `sampled_stance` and toxicity values |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_low_toxicity.csv` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_middle_toxicity.csv` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_high_toxicity.csv` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_all_strata.csv` (create or regenerate)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv` (read only)
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`

## Contracts to freeze

### Input columns

Require `cell`, `sample_toxicity_type`, and `sampled_stance` on the cohort.

### Strata

| Stratum key | `sample_toxicity_type` value | Output file |
|-------------|------------------------------|-------------|
| low | `sample_low_toxicity` | `stance_by_cell_low_toxicity.csv` |
| middle | `sample_middle_toxicity` | `stance_by_cell_middle_toxicity.csv` |
| high | `sample_high_toxicity` | `stance_by_cell_high_toxicity.csv` |

### Table shape

Each stratum CSV is a count table with:

- rows: `left`, `right` in that order
- columns: `unanimous_keep`, `majority_keep`, `majority_remove`, `unanimous_remove` in that order
- cell values: integer counts

Also write `stance_by_cell_all_strata.csv` in long form with columns `toxicity_stratum`, `sampled_stance`, `cell`, `n`.

### Rules

Use counts, not only percentages. Percentages may be added as extra columns if labeled clearly, but counts are required.

Do not use participant `political_affiliation` or related results full fields.

Do not run statistical tests.

## Exact commands

### 1. Run Analysis 3

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py
```

Expected: the four CSV paths under `outputs/analysis3/` exist.

### 2. Shape and total check

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd

long = pd.read_csv(
    "experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_all_strata.csv"
)
assert set(long.columns) >= {"toxicity_stratum", "sampled_stance", "cell", "n"}
assert long["n"].sum() == 3718
for name in (
    "stance_by_cell_low_toxicity.csv",
    "stance_by_cell_middle_toxicity.csv",
    "stance_by_cell_high_toxicity.csv",
):
    wide = pd.read_csv(
        f"experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/{name}",
        index_col=0,
    )
    assert list(wide.index) == ["left", "right"]
    assert list(wide.columns) == [
        "unanimous_keep",
        "majority_keep",
        "majority_remove",
        "unanimous_remove",
    ]
print("analysis3_ok", int(long["n"].sum()), long.groupby("toxicity_stratum")["n"].sum().to_dict())
PY
```

Expected stdout starts with `analysis3_ok 3718`.

## Pass / fail

Pass:

- Three wide tables and one long table exist.
- Long table counts sum to the cohort size.
- Row and column orders match the contract.

Fail:

- A single pooled stance table replaces the three strata tables.
- Participant politics columns are introduced.
- Missing cells are omitted from the column set instead of written as zero.

## Commit gate

Commit the Analysis 3 script and CSVs after the shape check passes.
