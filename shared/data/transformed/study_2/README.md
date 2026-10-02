# Study 2 keep/remove labels

Each row is one rated Study 2 post, and the decision is the majority linked-fate vote. Ties are `remove`.

You generate these rows with `transform.py`, and the registry name is `STUDY_2_KEEP_REMOVE_LABELS`.

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_2/transform.py
```

The script loads `STUDY_2_RESULTS_FULL` and `STUDY_2_STIMULI`.

Posts with exactly five labelers are also written as two subsets. `split_keep_remove_labels.py` reads `STUDY_2_KEEP_REMOVE_LABELS`. Unanimous posts have 0 or 5 remove votes, and they are registered as `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`. Split posts have 1, 2, 3, or 4 remove votes, and they are registered as `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Posts with any other number of labelers are left out of both subsets.

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_2/split_keep_remove_labels.py
```

Upload each regenerated CSV to S3 at the registry key before callers use `load_dataset`.

## Balanced keep and remove rows

Each source table has more keep rows than remove rows. You balance a table by running `upsample_keep_remove_labels.py` from the repo root. You copy rows from the smaller class, with replacement, until keep and remove have the same count. The random seed is 1, so a second run writes the same copied rows. Each copied row keeps the source `post_id`, so that id can appear more than once.

`keep_remove_label` is 0 for keep and 1 for remove. You do not filter by the number of labelers in this step. The unanimous and split filters stay in `split_keep_remove_labels.py`.

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_2/upsample_keep_remove_labels.py
```

| Source registry name | Output registry name | Source rows | Source keep | Source remove | Output rows | Output keep | Output remove |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `STUDY_2_KEEP_REMOVE_LABELS` | `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS` | 20,000 | 15,140 | 4,860 | 30,280 | 15,140 | 15,140 |
| `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | 4,051 | 3,743 | 308 | 7,486 | 3,743 | 3,743 |
| `STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | 9,941 | 7,281 | 2,660 | 14,562 | 7,281 | 7,281 |

These counts were measured on October 1, 2026 from the registered source objects.

The output objects are:

- `s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_labels.csv`
- `s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv`
- `s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv`

You write the local CSV files only when you run the script. You upload those files to the keys above before `load_dataset` can read the new registry names. Git ignores the CSV files.
