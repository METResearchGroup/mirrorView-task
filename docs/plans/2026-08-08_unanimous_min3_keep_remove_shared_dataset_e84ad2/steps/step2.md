# Step 2: Implement transform build/write with failing-then-passing checks

## Goal

Add `transform_keep_remove_labels_unanimous_min3.py` that builds and materializes the filtered keep/remove table from results-full per Step 1 contracts. Prove behavior with a small synthetic unit check first, then regenerate the real CSV and assert acceptance counts.

## Caller / unit of work

**Main caller:**

```text
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
```

Flow: load results-full (or accept `raw`) → slim linked-fate trials → per-post aggregate → filter `n_raters >= 3` and unanimous → write CSV → print row/decision summary.

**In scope:** new transform module + writing `keep_remove_labels_unanimous_min3.csv`.

**Out of scope:** registry entry (Step 3); `main.py` / README updates (Step 3); experiment migrations; refactoring BERTopic or existing `transform.py` to share helpers (duplicate the slim-trial filter locally; YAGNI on extraction).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | Slim-trial filter, text-stability assert, write pattern |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform_get_user_reflection_feedback.py` | Second transform script shape |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | Unanimous aggregation fields (`n_raters`, `n_unique_decisions`) |
| `/workspace/docs/plans/2026-08-08_unanimous_min3_keep_remove_shared_dataset_e84ad2/steps/step1.md` | Frozen contracts |

## Files allowed to change

- `/workspace/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` (create)
- `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv` (create / regenerate)

## Files forbidden to change

- `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py`
- `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv`
- `/workspace/shared/data/transformed/study_phase_2_part_2/user_reflection_feedback.csv`
- `/workspace/shared/data/registry.py` (Step 3)
- `/workspace/shared/data/transformed/study_phase_2_part_2/main.py` (Step 3)
- `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` (Step 3)
- `/workspace/shared/data/raw/**`
- `/workspace/experiments/**`

## Contracts to freeze (implementation)

### Module layout

Mirror `transform.py`:

1. Module docstring with run-from-repo-root command.
2. `OUTPUT_DIR = Path(__file__).resolve().parent`
3. `OUTPUT_CSV = OUTPUT_DIR / "keep_remove_labels_unanimous_min3.csv"`
4. `_OUTPUT_COLUMNS` = Step 1 column list in that order.
5. Private helpers for slim trials and unanimous-min3 aggregation (names may vary; behavior must match Step 1).
6. Public `build_keep_remove_labels_unanimous_min3` / `write_keep_remove_labels_unanimous_min3`.
7. `__main__` block that writes and prints `rows`, `decision` value counts, and `columns`.

### Error behavior

| Condition | Raise |
|-----------|-------|
| Missing `evaluation_mode`, `post_id`, or `decision` on raw | `KeyError` |
| Conflicting `original_text` / `mirror_text` for a kept post | `ValueError` |
| Empty result after filter | still write empty CSV with header columns (do not crash); full-data run must not be empty |

### Synthetic test design (write before / with implementation)

Given a tiny in-memory frame (do not require pytest package layout if none exists under `shared/`; an inline `python -c` / heredoc assertion is acceptable for this plan):

| post_id | n slim trials | decisions | Expect in output? |
|---------|---------------|-----------|-------------------|
| A | 3 | keep, keep, keep | yes, keep, `n_raters=3` |
| B | 3 | remove, remove, keep | no (not unanimous) |
| C | 2 | keep, keep | no (`n_raters < 3`) |
| D | 4 | remove × 4 | yes, remove, `n_raters=4` |

Assert: output `message_id` set == `{A, D}`; columns match Step 1; `keep_remove_label` correct.

## Exact commands

### 1. Synthetic check (must fail before implementation; pass after)

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
from shared.data.transformed.study_phase_2_part_2.transform_keep_remove_labels_unanimous_min3 import (
    build_keep_remove_labels_unanimous_min3,
)

raw = pd.DataFrame(
    [
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "A", "decision": "keep", "original_text": "oa", "mirror_text": "ma"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "remove", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "remove", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "B", "decision": "keep", "original_text": "ob", "mirror_text": "mb"},
        {"evaluation_mode": "linked_fate", "post_id": "C", "decision": "keep", "original_text": "oc", "mirror_text": "mc"},
        {"evaluation_mode": "linked_fate", "post_id": "C", "decision": "keep", "original_text": "oc", "mirror_text": "mc"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "remove", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "remove", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "remove", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "linked_fate", "post_id": "D", "decision": "remove", "original_text": "od", "mirror_text": "md"},
        {"evaluation_mode": "other", "post_id": "E", "decision": "keep", "original_text": "oe", "mirror_text": "me"},
        {"evaluation_mode": "other", "post_id": "E", "decision": "keep", "original_text": "oe", "mirror_text": "me"},
        {"evaluation_mode": "other", "post_id": "E", "decision": "keep", "original_text": "oe", "mirror_text": "me"},
    ]
)
out = build_keep_remove_labels_unanimous_min3(raw)
assert list(out.columns) == [
    "message_id", "original_text", "mirror_text", "decision", "keep_remove_label", "n_raters"
]
assert set(out["message_id"]) == {"A", "D"}
row_a = out.set_index("message_id").loc["A"]
row_d = out.set_index("message_id").loc["D"]
assert row_a["decision"] == "keep" and int(row_a["keep_remove_label"]) == 0 and int(row_a["n_raters"]) == 3
assert row_d["decision"] == "remove" and int(row_d["keep_remove_label"]) == 1 and int(row_d["n_raters"]) == 4
print("synthetic_ok")
PY
```

**Before implementation expected:** `ModuleNotFoundError` or `ImportError` (fail for the right reason).

**After implementation expected:**

```text
synthetic_ok
```

### 2. Materialize full CSV

```bash
cd /workspace
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
```

**Expected (shape):**

```text
Wrote .../keep_remove_labels_unanimous_min3.csv
rows=1644
{'keep': 1490, 'remove': 154}
columns=['message_id', 'original_text', 'mirror_text', 'decision', 'keep_remove_label', 'n_raters']
```

### 3. Confirm every row has `n_raters >= 3` and unanimous provenance

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
from pathlib import Path
p = Path("shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv")
df = pd.read_csv(p)
assert len(df) == 1644
assert (df["n_raters"] >= 3).all()
assert set(df["decision"]) <= {"keep", "remove"}
assert df["message_id"].is_unique
print("full_csv_ok", df["decision"].value_counts().to_dict())
PY
```

**Expected:**

```text
full_csv_ok {'keep': 1490, 'remove': 154}
```

## Pass / fail

**Pass**

- Synthetic heredoc prints `synthetic_ok`.
- Full script writes CSV with 1644 rows and keep/remove counts 1490/154.
- Column order matches Step 1.
- Existing `keep_remove_labels.csv` unchanged (`git diff` clean for that file).

**Fail**

- Includes posts with `n_raters < 3` or split decisions.
- Filters modal labels instead of results-full.
- Edits `registry.py` / `main.py` / README in this step.

## Commit gate

Commit the new transform module and materialized CSV together with a message such as:

`Add unanimous min-3 keep/remove transform and CSV for Part 2`

Do not register the dataset until Step 3.
