# Study Phase 2 Part 2 — transformed artifacts

Materialized CSVs derived from the raw Part 2 results.

## Source

- Registry: `STUDY_PHASE_2_PART_2_RESULTS_FULL`
- Path: `shared/data/raw/study_phase_2_part_2/results/full.csv`

## Scripts

| Script | Role |
| --- | --- |
| `transform.py` | Keep/remove modal labels only → `keep_remove_labels.csv` |
| `transform_get_user_reflection_feedback.py` | Per-user Phase 1 reflection feedback → `user_reflection_feedback.csv` |
| `main.py` | Runs both transforms (prefer this to regenerate everything) |

## Transforms

### Keep/remove modal labels (`transform.py`)

1. Keep `evaluation_mode == "linked_fate"` (case-insensitive).
2. Keep `decision ∈ {keep, remove}` (case-insensitive).
3. Drop null / empty `post_id` (before stringifying, so NaN never becomes `"nan"`).
4. Assert each `post_id` has exactly one distinct `original_text` and one distinct `mirror_text`.
5. Modal decision per `post_id`; **ties → `remove`** (`keep` only if `keep_count > remove_count`).
6. `keep_remove_label`: `1` = remove, `0` = keep.
7. Expose `message_id` as an alias of `post_id`.

**Output**

- File: `keep_remove_labels.csv`
- Registry: `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`
- Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`
- Expected size: ~8791 rows (~5978 keep / ~2813 remove)

### User reflection feedback (`transform_get_user_reflection_feedback.py`)

Per-participant Phase 1 reflection survey answers after linked-fate keep/remove trials.

1. Keep `trial_type == "survey-html-form"` (export plugin type; jsPsych tag was `phase1-reflection-survey`).
2. Keep rows with non-empty `phase1_pair_reflection_text` (drop null / empty / literal `"nan"`).
3. Drop null / empty `participant_id`.
4. Coerce `phase1_pair_influence_rating` to numeric (`errors="coerce"`).
5. One row per `participant_id`; source data is unique, but if duplicates appear **keep first** in source-row order.

**Output**

- File: `user_reflection_feedback.csv`
- Registry: `STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK`
- Columns: `participant_id`, `prolific_id`, `phase1_pair_reflection_text`, `phase1_pair_influence_rating`
- Expected size: ~1177 rows (one per participant with usable reflection text)

## Regenerate

Both artifacts (recommended):

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/main.py
```

Keep/remove only:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform.py
```

User reflection feedback only:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_get_user_reflection_feedback.py
```
