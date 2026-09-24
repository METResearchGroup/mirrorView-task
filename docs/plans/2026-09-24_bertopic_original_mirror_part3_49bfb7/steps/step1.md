# Step 1: Build Part 3 keep/remove label table

## Goal

Add `shared/data/transformed/study_phase_2_part_3/keep_remove_labels.csv` by reusing Part 2 modal-aggregation logic. Ties become `remove`. Join scored linked-fate Part 3 results to Part 3 stimuli for stable text and metadata. Register `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` in `shared/data/registry.py`. Expose per-post rater counts and keep rate. Do **not** apply the min-3-rater filter (analysis-time only per the Decisions table). Add unit tests.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_3/transform.py
```

**Registry load check:**

```bash
PYTHONPATH=. uv run python -c "
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS
df = load_dataset(STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS, low_memory=False)
print('rows', len(df), 'cols', list(df.columns))
"
```

**In scope:** Part 3 transform module, README, generated CSV, registry entry, unit tests.

**Out of scope:** Min-rater filtering, experiment scaffold, embeddings, BERTopic, edits to Part 2 transforms.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | `_load_slim_trial_frame`, `_aggregate_modal_labels` patterns to port |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Modal label contract and column names |
| `/workspace/shared/data/registry.py` | Existing Part 3 raw entries; add transformed entry |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/raw/study_phase_2_part_3/results/full.csv` | `post_id`, `decision`, `evaluation_mode`, `mirror_text` |
| `/workspace/shared/data/raw/study_phase_2_part_3/stimuli/flips.csv` | `post_primary_key`, `original_text`, `mirrored_text`, `sampled_stance`, `sample_toxicity_type` |

**Verified join key (do not change):** `results.post_id` (stripped string) equals `stimuli.post_primary_key` (stripped string). Inner join on all 79,500 linked-fate scored rows yields 79,500 rows and 18,866 unique posts. All 18,866 rated `post_id` values exist in stimuli; 33 stimulus posts have no ratings.

## Files allowed to change

- `/workspace/shared/data/transformed/study_phase_2_part_3/transform.py` (create)
- `/workspace/shared/data/transformed/study_phase_2_part_3/README.md` (create)
- `/workspace/shared/data/transformed/study_phase_2_part_3/keep_remove_labels.csv` (create via transform script)
- `/workspace/shared/data/registry.py` (add `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` constant and `DATASETS` entry)
- `/workspace/tests/shared/data/transformed/study_phase_2_part_3/test_transform.py` (create)

## Files forbidden to change

- `/workspace/shared/data/transformed/study_phase_2_part_2/**`
- `/workspace/experiments/**`
- `/workspace/pyproject.toml`
- `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md`
- Any other file

## Implementation details

### Module: `shared/data/transformed/study_phase_2_part_3/transform.py`

Port and extend Part 2 logic. Public functions:

1. `STIMULI_JOIN_KEY = "post_primary_key"`
2. `RESULTS_JOIN_KEY = "post_id"`
3. `OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_labels.csv"`

4. `_load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame`  
   Same rules as Part 2 `transform.py`:
   - `evaluation_mode == "linked_fate"` (case-insensitive)
   - `decision in {"keep", "remove"}` (case-insensitive)
   - Drop null, empty, or literal `"nan"` `post_id` before stringifying
   - Normalize `post_id` to stripped string

5. `_aggregate_modal_labels_with_counts(trials: pd.DataFrame) -> pd.DataFrame`  
   Per `post_id`:
   - `n_keep`, `n_remove`, `n_raters = n_keep + n_remove`
   - `keep_rate = n_keep / n_raters` (float)
   - `decision = "keep"` iff `n_keep > n_remove`, else `"remove"` (ties become `remove`)
   - `keep_remove_label = 1` for `remove`, `0` for `keep`
   - Raise `ValueError` if any `post_id` has conflicting `original_text` or `mirror_text` across trials (use results columns for the stability check)

6. `_join_stimuli_metadata(modal: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame`  
   - Left join `modal` to stimuli on `modal.post_id == stimuli.post_primary_key.astype(str).str.strip()`
   - Raise `ValueError` if any modal `post_id` lacks a stimuli row (expected 0 missing)
   - Take `original_text` and `mirror_text` from **stimuli** (`mirrored_text` renamed to `mirror_text`)
   - Take `sampled_stance`, `sample_toxicity_type` from stimuli
   - `platform = post_id.str.split("_", n=1).str[0]` (verified values: `reddit`, `bluesky`, `twitter`)

7. `build_keep_remove_labels(raw: pd.DataFrame | None = None, stimuli: pd.DataFrame | None = None) -> pd.DataFrame`  
   Loads `STUDY_PHASE_2_PART_3_RESULTS_FULL` and `STUDY_PHASE_2_PART_3_STIMULI` when omitted.

8. `write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame`

### Output schema (`keep_remove_labels.csv`)

| Column | Type | Source / rule |
|--------|------|----------------|
| `post_id` | str | `results.post_id` (stripped); primary key |
| `original_text` | str | stimuli |
| `mirror_text` | str | stimuli `mirrored_text` renamed |
| `decision` | str | modal; `keep` or `remove` |
| `keep_remove_label` | int | `1` = remove, `0` = keep |
| `n_raters` | int | scored linked-fate trials per post |
| `keep_rate` | float | `n_keep / n_raters` |
| `n_keep` | int | keep votes |
| `n_remove` | int | remove votes |
| `sampled_stance` | str | stimuli |
| `sample_toxicity_type` | str | stimuli |
| `platform` | str | first `_`-delimited token of `post_id` |

**Expected row count:** 18,866 (all rated posts). **Do not** filter `n_raters >= 3`.

**Expected decision mix (approximate):** keep ~13,604, remove ~5,262; mean `keep_rate` ~0.700.

### Registry entry

Add to `shared/data/registry.py`:

```python
STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS = "STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS"
```

```python
STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS: DatasetEntry(
    name=STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS,
    relative_path=Path(
        "shared/data/transformed/study_phase_2_part_3/keep_remove_labels.csv"
    ),
    kind="transformed",
    study_phase="study_phase_2_part_3",
),
```

## TDD tests to write first

File: `/workspace/tests/shared/data/transformed/study_phase_2_part_3/test_transform.py`

Write these tests **before** implementation. Use small synthetic frames (no full CSV reads in unit tests).

| Test name | Given | Assert |
|-----------|-------|--------|
| `test_load_slim_trial_frame_filters_linked_fate_keep_remove` | Raw frame with linked_fate keep/remove, other modes, empty post_id | Only valid linked-fate rows remain |
| `test_modal_tie_becomes_remove` | One post_id with 2 keep + 2 remove votes | `decision == "remove"`, `keep_remove_label == 1` |
| `test_modal_keep_majority` | One post_id with 3 keep + 1 remove | `decision == "keep"`, `keep_rate == 0.75`, `n_raters == 4` |
| `test_join_stimuli_adds_platform_and_mirror_text` | Modal row + stimuli with `post_primary_key`, `mirrored_text` | `mirror_text` populated; `platform == "reddit"` for `reddit_abc` |
| `test_build_raises_when_stimuli_missing_post` | Modal post_id absent from stimuli | `ValueError` |
| `test_output_columns_exact_order` | Full `build_keep_remove_labels` on synthetic end-to-end mini fixture | Columns match schema list exactly |

Optional integration test (may use real CSVs, mark `@pytest.mark.integration` if added):

| Test name | Assert |
|-----------|--------|
| `test_live_row_count_and_join_coverage` | `len(df) == 18866`; no null `post_id`, `original_text`, `mirror_text`, `platform` |

## Exact commands

```bash
cd /workspace

# 1. Run tests (expect FAIL before implementation)
PYTHONPATH=. uv run pytest tests/shared/data/transformed/study_phase_2_part_3/test_transform.py -v

# 2. Generate artifact
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_3/transform.py
```

Expected transform stdout (approximate):

```text
Wrote shared/data/transformed/study_phase_2_part_3/keep_remove_labels.csv
rows=18866
decision={'keep': 13604, 'remove': 5262}
columns=['post_id', 'original_text', 'mirror_text', 'decision', 'keep_remove_label', 'n_raters', 'keep_rate', 'n_keep', 'n_remove', 'sampled_stance', 'sample_toxicity_type', 'platform']
```

```bash
# 3. Registry load check
PYTHONPATH=. uv run python -c "
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS, resolve_path
import pandas as pd
path = resolve_path(STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS)
df = load_dataset(STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS, low_memory=False)
assert len(df) == 18866
assert df['n_raters'].min() >= 1
assert set(df['decision']) <= {'keep', 'remove'}
assert df['platform'].isin(['reddit','bluesky','twitter']).all()
print('registry OK', path, 'rows', len(df), 'mean_keep_rate', round(df['keep_rate'].mean(), 4))
"

# 4. Re-run tests (expect PASS)
PYTHONPATH=. uv run pytest tests/shared/data/transformed/study_phase_2_part_3/test_transform.py -v
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Join key | `post_id == post_primary_key` on all 18,866 rated posts | Any rated post missing stimuli |
| Row count | 18,866 | Any other count |
| Min-rater filter | Not applied; posts with `n_raters == 1` remain | Rows dropped at `n_raters < 3` |
| Modal ties | `n_keep == n_remove` yields `remove` | Ties yield `keep` |
| Columns | Exact schema above | Missing or misnamed columns |
| Registry | `load_dataset(STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS)` works | KeyError / FileNotFoundError |
| Tests | All unit tests green | Any failure |
| Isolation | No edits under `experiments/` or Part 2 transforms | Diff outside allowed set |

## Commit message(s)

```
Add Part 3 keep/remove label transform and registry entry

Build modal labels from linked-fate results joined to stimuli on
post_id == post_primary_key. Expose n_raters and keep_rate without
min-rater filtering. Add unit tests.
```
