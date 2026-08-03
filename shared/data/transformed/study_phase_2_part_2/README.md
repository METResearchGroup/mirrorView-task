# Study Phase 2 Part 2 — keep/remove modal labels

Materialized post-level training labels derived from the raw Part 2 results.

## Source

- Registry: `STUDY_PHASE_2_PART_2_RESULTS_FULL`
- Path: `shared/data/raw/study_phase_2_part_2/results/full.csv`

## Transform

1. Keep `evaluation_mode == "linked_fate"` (case-insensitive).
2. Keep `decision ∈ {keep, remove}` (case-insensitive).
3. Drop null / empty `post_id` (before stringifying, so NaN never becomes `"nan"`).
4. Assert each `post_id` has exactly one distinct `original_text` and one distinct `mirror_text`.
5. Modal decision per `post_id`; **ties → `remove`** (`keep` only if `keep_count > remove_count`).
6. `keep_remove_label`: `1` = remove, `0` = keep.
7. Expose `message_id` as an alias of `post_id`.

## Output

- File: `keep_remove_labels.csv`
- Registry: `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`
- Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`
- Expected size: ~8791 rows (~5978 keep / ~2813 remove)

## Regenerate

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform.py
```
