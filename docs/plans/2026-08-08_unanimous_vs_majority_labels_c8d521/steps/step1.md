# Step 1: Freeze the cohort contract and write the four cell table

## Goal

Lock the four cell rules, the joins for toxicity and stance, the expected counts, and the local cohort path. Then implement a builder that writes one experiment local cohort file that Steps 2 through 4 read.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py
```

Flow: load Phase 2 Part 2 results full, keep linked fate keep or remove trials with a usable post id, aggregate per post, keep posts with at least three raters, drop exact ties, assign one of four cells, join stimuli fields, write the cohort CSV, print cell counts.

In scope: freeze the contracts below, add the builder module, write the cohort CSV under the experiment folder.

Out of scope: Analysis 1 through 3 scripts, README or RESULTS rewrites, shared registry changes, tie analysis.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` | Locked design |
| `/Users/mark/src/work/mirrorview-wt/experiments/bertopic_modeling_2026_08_05/src/data.py` | Slim trial filter and per post keep count, remove count, unanimous flag |
| `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` | Unanimous min three transform precedent |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Registry names for results full and stimuli |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/plan.md` | Executive summary |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/__init__.py` (create if missing)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv` (create or regenerate)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/rater_agreement_2026_08_06/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/README.md` (Step 5)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md`

## Contracts to freeze

### Slim trial gate

Start from `STUDY_PHASE_2_PART_2_RESULTS_FULL`. Keep a row only when all of the following hold:

1. `evaluation_mode` equals `linked_fate` after lowercasing and stripping.
2. `decision` is `keep` or `remove` after lowercasing and stripping.
3. `post_id` is non null, non empty after stripping, and not the literal string `nan`.

Assert that each kept `post_id` has exactly one distinct `original_text` and one distinct `mirror_text` among slim trials. Raise `ValueError` on conflict.

### Per post fields

For each `post_id` after the slim trial gate:

- `n_raters` is the number of slim trial rows
- `keep_count` is the number of keep decisions
- `remove_count` is the number of remove decisions
- `is_unanimous` is true when the number of distinct decisions equals 1

### Universe and cells

Keep posts with `n_raters >= 3` only.

Drop exact ties, defined as `keep_count == remove_count`.

Assign `cell` with these exact strings:

| Condition | `cell` value |
|-----------|--------------|
| `is_unanimous` and `keep_count == n_raters` | `unanimous_keep` |
| `is_unanimous` and `remove_count == n_raters` | `unanimous_remove` |
| not unanimous, `keep_count > remove_count` | `majority_keep` |
| not unanimous, `remove_count > keep_count` | `majority_remove` |

### Stimuli join

Join `STUDY_PHASE_2_PART_2_STIMULI` on `post_id == post_primary_key`.

Required joined columns:

- `sample_toxicity_type` with values `sample_low_toxicity`, `sample_middle_toxicity`, `sample_high_toxicity`
- `sampled_stance` with values `left` or `right`
- `original_text` from stimuli may be used to confirm the results text, but the cohort must store the stable `original_text` and `mirror_text` from the slim trials after the uniqueness assert

Every cohort row must find exactly one stimuli row. Raise `ValueError` if a cohort post is missing from stimuli.

### Output path and columns

Path: `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv`

Column order:

| Column | Meaning |
|--------|---------|
| `message_id` | string alias of `post_id` |
| `original_text` | stable original post text |
| `mirror_text` | stable mirror text |
| `cell` | one of the four cell strings above |
| `n_raters` | integer at least 3 |
| `keep_count` | integer |
| `remove_count` | integer |
| `is_unanimous` | boolean |
| `sample_toxicity_type` | stimuli toxicity stratum |
| `sampled_stance` | `left` or `right` |

### Acceptance counts on current data

| `cell` | Expected rows |
|--------|---------------|
| `unanimous_keep` | 1490 |
| `majority_keep` | 1480 |
| `majority_remove` | 594 |
| `unanimous_remove` | 154 |
| total | 3718 |

If the count command below differs, stop and revise this plan before Step 2.

### Public API names frozen for the builder

| Symbol | Role |
|--------|------|
| `COHORT_CSV` | Path to `four_cell_cohort.csv` |
| `build_four_cell_cohort(raw=None, stimuli=None) -> DataFrame` | Pure build |
| `write_four_cell_cohort(path=COHORT_CSV) -> DataFrame` | Write CSV and return the frame |

## Exact commands

### 1. Reconfirm cell counts before coding

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
trials = raw.copy()
trials["evaluation_mode"] = trials["evaluation_mode"].astype(str).str.lower().str.strip()
trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
trials = trials[trials["evaluation_mode"] == "linked_fate"]
trials = trials[trials["decision"].isin(["keep", "remove"])]
trials = trials[trials["post_id"].notna()].copy()
trials["post_id"] = trials["post_id"].astype(str).str.strip()
trials = trials[(trials["post_id"] != "") & (trials["post_id"].str.lower() != "nan")]
g = trials.groupby("post_id").agg(
    n_raters=("decision", "size"),
    n_unique=("decision", "nunique"),
    keep_count=("decision", lambda s: int((s == "keep").sum())),
    remove_count=("decision", lambda s: int((s == "remove").sum())),
)
g = g[g["n_raters"] >= 3]
g = g[g["keep_count"] != g["remove_count"]]
uni = g["n_unique"] == 1
cell = []
for idx, row in g.iterrows():
    if bool(uni.loc[idx]) and row["keep_count"] == row["n_raters"]:
        cell.append("unanimous_keep")
    elif bool(uni.loc[idx]) and row["remove_count"] == row["n_raters"]:
        cell.append("unanimous_remove")
    elif row["keep_count"] > row["remove_count"]:
        cell.append("majority_keep")
    else:
        cell.append("majority_remove")
g = g.copy()
g["cell"] = cell
print(g["cell"].value_counts().to_dict())
print({"total": len(g)})
PY
```

Expected stdout keys and values:

```text
unanimous_keep: 1490
majority_keep: 1480
majority_remove: 594
unanimous_remove: 154
total: 3718
```

### 2. Synthetic builder check (must fail before implementation, pass after)

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
from experiments.unanimous_vs_majority_labels_2026_08_08.src.build_cohort import (
    build_four_cell_cohort,
)

raw = pd.DataFrame(
    [
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "keep", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "keep", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "remove", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "C", "decision": "remove", "original_text": "oc", "mirror_text": "mc"},
        {"evaluation_mode": "linked_fate", "post_id": "C", "decision": "keep", "original_text": "oc", "mirror_text": "mc"},
        {"evaluation_mode": "linked_fate", "post_id": "C", "decision": "remove", "original_text": "oc", "mirror_text": "mc"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "keep", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "remove", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "linked_fate", "post_id": "E", "decision": "remove", "original_text": "oe", "mirror_text": "me"},
        {"evaluation_mode": "linked_fate", "post_id": "E", "decision": "remove", "original_text": "oe", "mirror_text": "me"},
        {"evaluation_mode": "linked_fate", "post_id": "E", "decision": "remove", "original_text": "oe", "mirror_text": "me"},
    ]
)
stimuli = pd.DataFrame(
    [
        {"post_primary_key": "A", "sample_toxicity_type": "sample_low_toxicity", "sampled_stance": "left", "original_text": "oa", "mirrored_text": "ma"},
        {"post_primary_key": "B", "sample_toxicity_type": "sample_middle_toxicity", "sampled_stance": "right", "original_text": "ob", "mirrored_text": "mb"},
        {"post_primary_key": "C", "sample_toxicity_type": "sample_high_toxicity", "sampled_stance": "left", "original_text": "oc", "mirrored_text": "mc"},
        {"post_primary_key": "D", "sample_toxicity_type": "sample_low_toxicity", "sampled_stance": "right", "original_text": "od", "mirrored_text": "md"},
        {"post_primary_key": "E", "sample_toxicity_type": "sample_high_toxicity", "sampled_stance": "left", "original_text": "oe", "mirrored_text": "me"},
    ]
)
out = build_four_cell_cohort(raw=raw, stimuli=stimuli)
assert set(out["message_id"]) == {"A", "B", "C", "E"}
assert out.set_index("message_id").loc["A", "cell"] == "unanimous_keep"
assert out.set_index("message_id").loc["B", "cell"] == "majority_keep"
assert out.set_index("message_id").loc["C", "cell"] == "majority_remove"
assert out.set_index("message_id").loc["E", "cell"] == "unanimous_remove"
print("synthetic_ok", len(out))
PY
```

Expected after implementation:

```text
synthetic_ok 4
```

Post A is unanimous keep. Post B is majority keep. Post C is majority remove. Post E is unanimous remove. Post D has only two raters, so the builder must drop it.

### 3. Write the real cohort and print counts

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py
```

Expected: printed cell counts match the acceptance table, and `outputs/cohort/four_cell_cohort.csv` exists with 3718 rows.

## Pass / fail

Pass:

- Count command matches 1490 / 1480 / 594 / 154.
- Synthetic check prints `synthetic_ok 4`.
- Real cohort CSV has 3718 rows and the frozen columns in order.

Fail:

- Counts drift without a plan revision.
- Ties appear in the cohort.
- Missing stimuli join rows are silently dropped.

## Commit gate

Commit the builder and the cohort CSV after the real write command matches acceptance counts.
