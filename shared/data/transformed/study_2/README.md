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
