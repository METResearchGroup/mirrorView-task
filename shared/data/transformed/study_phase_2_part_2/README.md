# Study Phase 2 Part 2 transformed artifacts

Materialized CSVs derived from the raw Part 2 results.

## Source

- Registry: `STUDY_PHASE_2_PART_2_RESULTS_FULL`
- Path: `shared/data/raw/study_phase_2_part_2/results/full.csv`

## Scripts

| Script | Role |
| --- | --- |
| `transform.py` | Keep/remove modal labels only, written to `keep_remove_labels.csv` |
| `transform_get_user_reflection_feedback.py` | Per-user Phase 1 reflection feedback, written to `user_reflection_feedback.csv` |
| `transform_keep_remove_labels_unanimous_min3.py` | Unanimous min-3 keep/remove labels, written to `keep_remove_labels_unanimous_min3.csv` |
| `main.py` | Runs all three transforms. Prefer this when regenerating everything. |

## Transforms

### Keep/remove modal labels (`transform.py`)

1. Keep `evaluation_mode == "linked_fate"` (case-insensitive).
2. Keep `decision` in `{keep, remove}` (case-insensitive).
3. Drop null or empty `post_id` before stringifying, so NaN never becomes `"nan"`.
4. Assert each `post_id` has exactly one distinct `original_text` and one distinct `mirror_text`.
5. Take the modal decision per `post_id`. Ties become `remove`. Keep only if `keep_count > remove_count`.
6. Set `keep_remove_label` to `1` for remove and `0` for keep.
7. Expose `message_id` as an alias of `post_id`.

**Output**

- File: `keep_remove_labels.csv`
- Registry: `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`
- Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`
- Expected size: about 8791 rows (about 5978 keep / 2813 remove)

### User reflection feedback (`transform_get_user_reflection_feedback.py`)

Per-participant Phase 1 reflection survey answers after linked-fate keep/remove trials.

1. Keep `trial_type == "survey-html-form"` (export plugin type; the jsPsych tag was `phase1-reflection-survey`).
2. Keep rows with non-empty `phase1_pair_reflection_text` (drop null, empty, or literal `"nan"`).
3. Drop null or empty `participant_id`.
4. Coerce `phase1_pair_influence_rating` to numeric (`errors="coerce"`).
5. Keep one row per `participant_id`. The source data is unique, but if duplicates appear, keep the first row in source-row order.

**Output**

- File: `user_reflection_feedback.csv`
- Registry: `STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK`
- Columns: `participant_id`, `prolific_id`, `phase1_pair_reflection_text`, `phase1_pair_influence_rating`
- Expected size: about 1177 rows (one per participant with usable reflection text)

### Unanimous min-3 keep/remove labels (`transform_keep_remove_labels_unanimous_min3.py`)

High-agreement subset derived from results-full (not a filter of the modal labels CSV).

1. Apply the same linked-fate keep/remove slim-trial filter as modal labels (steps 1–4 above).
2. Aggregate per `post_id`: `n_raters`, unique decisions, keep/remove counts.
3. Keep posts where `n_raters >= 3` and all raters share the same decision (unanimous).
4. Set `decision` to that shared label; set `keep_remove_label` to `1` for remove and `0` for keep.
5. Expose `message_id` as an alias of `post_id` and include `n_raters`.

**Output**

- File: `keep_remove_labels_unanimous_min3.csv`
- Registry: `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3`
- Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`, `n_raters`
- Expected size: about 1644 rows (about 1490 keep / 154 remove)

## Regenerate

All three artifacts (recommended):

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/main.py
```

Keep/remove modal labels only:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform.py
```

User reflection feedback only:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_get_user_reflection_feedback.py
```

Unanimous min-3 keep/remove labels only:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
```
