# Step 3: Register dataset, wire regeneration, document

## Goal

Expose the materialized CSV through the shared registry and dataloader, include it in Part 2 transform regeneration (`main.py`), and document the artifact in the transformed README so callers can load it by name.

## Caller / unit of work

**Main caller:**

```python
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3

df = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3, low_memory=False)
```

Secondary caller: `PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/main.py` regenerates modal labels, reflection feedback, **and** the new unanimous-min3 CSV.

**In scope:** `registry.py` entry, `main.py` wiring, README section, load smoke check.

**Out of scope:** changing transform logic from Step 2; migrating BERTopic or other experiments to the new name; deleting or altering modal labels.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/registry.py` | Pattern for `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/shared/data/dataloader.py` | Confirm no loader changes needed (name-only registry) |
| `/workspace/shared/data/transformed/study_phase_2_part_2/main.py` | How existing transforms are invoked |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Section structure to extend |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv` | Must already exist from Step 2 |
| `/workspace/docs/plans/2026-08-08_unanimous_min3_keep_remove_shared_dataset_e84ad2/steps/step1.md` | Frozen name/path/columns/counts |

## Files allowed to change

- `/workspace/shared/data/registry.py` (add constant + `DATASETS` entry only)
- `/workspace/shared/data/transformed/study_phase_2_part_2/main.py` (import + call write helper; update module docstring)
- `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` (document new transform + regenerate commands)

## Files forbidden to change

- `/workspace/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` (logic frozen in Step 2; only re-run if regenerating)
- `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py`
- `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv`
- `/workspace/shared/data/dataloader.py` (no API change)
- `/workspace/shared/data/raw/**`
- `/workspace/experiments/**`

## Contracts to freeze

### Registry

Add alongside other Part 2 entries:

```text
STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3
  relative_path = shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv
  kind = transformed
  study_phase = study_phase_2_part_2
```

Export the string constant at module top with the other names.

### `main.py`

After writing keep/remove modal labels and user reflection feedback (preserve existing order of those two), also call `write_keep_remove_labels_unanimous_min3()` and print path, row count, decision value counts, and columns (same print style as the other artifacts).

### README section (required content)

Add a subsection parallel to “Keep/remove modal labels”:

1. Source: `STUDY_PHASE_2_PART_2_RESULTS_FULL`.
2. Steps: slim linked-fate filter; require `n_raters >= 3`; require unanimous decisions; set `decision` / `keep_remove_label`; expose `n_raters`; `message_id` alias.
3. Output file, registry name, column list, expected size (~1644 rows; ~1490 keep / ~154 remove).
4. Note that this is **not** a filter of the modal labels CSV.
5. Update the Scripts table and Regenerate commands to include the new module and mention `main.py` regenerates all three.

## Exact commands

### 1. Load by registry name

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3

df = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3, low_memory=False)
assert len(df) == 1644
assert list(df.columns) == [
    "message_id", "original_text", "mirror_text", "decision", "keep_remove_label", "n_raters"
]
assert (df["n_raters"] >= 3).all()
print(df["decision"].value_counts().to_dict())
PY
```

**Expected:**

```text
{'keep': 1490, 'remove': 154}
```

### 2. Full regenerate smoke

```bash
cd /workspace
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/main.py
```

**Expected:** prints for all three artifacts, including the unanimous-min3 CSV with `rows=1644` and keep/remove counts `1490` / `154`. Modal labels row count remains ~8791 (unchanged contract).

### 3. Modal labels untouched

```bash
cd /workspace
git diff --stat -- shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv
```

**Expected:** empty diff (file not modified), or only whitespace-identical rewrite if `main.py` rewrote it bit-identically. Prefer confirming decision counts still ~5978 keep / ~2813 remove via a quick load if the file was rewritten.

## Pass / fail

**Pass**

- `load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3)` returns 1644 rows with frozen columns.
- `main.py` regenerates the new CSV successfully.
- README documents the filter, registry name, and expected size.
- Modal registry entry and its scientific contract unchanged.

**Fail**

- Hardcoded paths in callers/docs instead of registry name.
- Loader changes required (should not be).
- Experiment code under `experiments/` modified.

## Commit gate

Commit registry + `main.py` + README (and any intentional CSV refresh) with a message such as:

`Register unanimous min-3 Part 2 keep/remove shared dataset`

After this commit, the plan’s “done” checklist in `plan.md` should all hold.
