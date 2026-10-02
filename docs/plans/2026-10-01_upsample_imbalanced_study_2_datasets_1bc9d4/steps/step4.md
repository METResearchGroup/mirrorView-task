# Step 4: Implement the Study 2 dataset writer

## Goal

Complete the single caller path from registered source to ignored local CSV. Keep source filtering in the existing Study 2 transforms, and keep S3 publication outside the Python generation command.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/steps/step2.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/steps/step3.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/transform.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- Every file under `/Users/mark/src/work/mirrorview-wt/tests/`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`

## Implementation order

Implement the caller in dependency order:

1. Define the approved source and output registry pairs as one stable tuple.
2. For each pair, load the source through `dataloader.load_dataset` with `low_memory=False`.
3. Pass the full source frame to `upsample_df` with `keep_remove_label`. Do not filter by `n_raters`, `n_remove`, or `is_unanimous`.
4. Resolve the local output with `registry.resolve_path` and create only its parent directory.
5. Write the balanced frame with `index=False`.
6. Return the frames in a dictionary whose insertion order matches the approved pair order.
7. Have `main()` print the approved name, absolute path, row count, and sorted class count dictionary for each frame.

Do not add S3 code, overwrite checks for the ignored local files, command line options, hardcoded source row counts, or another schema.

## Commands and expected output

Run the real local generation command from the repository root:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_2/upsample_keep_remove_labels.py
```

Expected output:

```text
UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS path=/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsampled_keep_remove_labels.csv rows=30280 class_counts={0: 15140, 1: 15140}
UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS path=/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv rows=7486 class_counts={0: 3743, 1: 3743}
UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS path=/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv rows=14562 class_counts={0: 7281, 1: 7281}
```

Check the generated CSVs against their registered sources:

```bash
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd

from shared.data import registry
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)

pairs = (
    (STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, 30_280, {0: 15_140, 1: 15_140}, 10_280),
    (STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, 7_486, {0: 3_743, 1: 3_743}, 3_435),
    (STUDY_2_KEEP_REMOVE_SPLIT_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS, 14_562, {0: 7_281, 1: 7_281}, 4_621),
)
for source_name, output_name, rows, counts, repeated_ids in pairs:
    source = load_dataset(source_name, low_memory=False)
    output = pd.read_csv(registry.resolve_path(output_name), low_memory=False)
    assert len(output) == rows
    assert output["keep_remove_label"].value_counts().sort_index().to_dict() == counts
    assert list(output.columns) == list(source.columns)
    assert output["post_id"].duplicated().sum() == repeated_ids
    assert set(source["post_id"].astype(str)) <= set(output["post_id"].astype(str))
    print(output_name, len(output), counts, repeated_ids)
PY
```

Expected output:

```text
UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS 30280 {0: 15140, 1: 15140} 10280
UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS 7486 {0: 3743, 1: 3743} 3435
UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS 14562 {0: 7281, 1: 7281} 4621
```

Confirm Git ignores all three generated files:

```bash
git check-ignore -v shared/data/transformed/study_2/upsampled_keep_remove_labels.csv shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv
```

Expected output: three lines name the repository `*.csv` ignore rule.

Inspect and commit only the caller implementation:

```bash
git diff --check -- shared/data/transformed/study_2/upsample_keep_remove_labels.py
git diff --name-only -- shared/data/transformed/study_2/upsample_keep_remove_labels.py
git add shared/data/transformed/study_2/upsample_keep_remove_labels.py
git commit -m "Write balanced Study 2 datasets"
```

Expected output: the first command prints nothing. The second command lists only the writer module. Git creates one commit named `Write balanced Study 2 datasets` containing only that file. The generated CSV files are absent from the commit.

## Pass

- The generation command prints the three exact lines and writes the three exact files.
- Direct checks confirm the output row counts, class balance, columns, repeated IDs, and source coverage.
- The output with all labels includes source rows with labeler counts other than five.
- Git ignores every generated CSV.

## Fail

- The caller repeats the unanimous or split filters.
- A generated CSV contains an index column or a changed source column.
- The command contacts S3.
- A source transform, registry entry, or helper changes in this commit.
