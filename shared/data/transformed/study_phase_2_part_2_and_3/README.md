# Study Phase 2 Part 2 and Part 3 transformed artifacts

Materialized keep/remove label CSVs derived from the combined Part 2 and Part 3
results table (not from separate Part 2 and Part 3 concatenation in this repo).

## Source

- Registry: `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`
- S3 key: `shared/data/raw/study_phase_2_part_2_and_3/results/full.csv` in
  `mirrorview-experimental-artifacts`

`load_dataset` reads that object. Regenerated label CSVs are not visible until
they are uploaded to their registry keys under this directory.

## Scripts

| Script | Role |
| --- | --- |
| `transform.py` | Modal keep/remove labels → `keep_remove_labels.csv` |
| `transform_keep_remove_labels_unanimous_min3.py` | Unanimous min-3 labels → `keep_remove_labels_unanimous_min3.csv` |

Both scripts load the union results-full table, apply
`filter_keep_remove_trials(..., dedupe_worker_post=True)`, then aggregate with
`aggregate_modal_labels` or `aggregate_unanimous_labels(min_raters=3)`.

## Expected sizes (union raw table)

| Artifact | Registry | Rows (keep / remove) |
| --- | --- | --- |
| Modal labels | `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` | 20,000 (15,196 / 4,804) |
| Unanimous min-3 | `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` | 5,715 (5,280 / 435) |

After dedupe, linked-fate keep/remove trial rows: 100,606.

## Regenerate

Modal labels:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2_and_3/transform.py
```

Unanimous min-3 labels:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2_and_3/transform_keep_remove_labels_unanimous_min3.py
```
