# Step 3: Implement deterministic DataFrame upsampling

## Goal

Implement only `upsample_df`, the deepest dependency in the caller path. Verify it against the three live registered source datasets without writing files or adding test files.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/steps/step2.md`
- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`
- Every file under `/Users/mark/src/work/mirrorview-wt/tests/`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`

## Implementation order

Implement the confirmed contract without adding private framework code:

1. Access `df[class_label]` first so a missing column raises `KeyError`.
2. Reject the frame with `ValueError` when that Series contains any null value.
3. Count classes without changing the order in which they first appear.
4. Return an independent copy with a reset index when there is no smaller class to sample.
5. For each smaller class in that order, select its rows and call `DataFrame.sample` with replacement, the exact deficit, and `random_state`.
6. Concatenate the original frame followed by the sampled additions with `ignore_index=True`.
7. Return the result without modifying the input or changing columns and dtypes.

Use pandas only. Do not shuffle the completed output and do not add balancing weights, audit columns, synthetic IDs, or a second public function.

## Commands and expected output

Run the helper against the three registered source datasets. The command checks the exact output counts, class balance, source columns, dtypes, original row prefix, and source immutability:

```bash
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)
from shared.utils.upsample import upsample_df

expected = {
    STUDY_2_KEEP_REMOVE_LABELS: (30_280, {0: 15_140, 1: 15_140}),
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS: (7_486, {0: 3_743, 1: 3_743}),
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS: (14_562, {0: 7_281, 1: 7_281}),
}
for name, (rows, counts) in expected.items():
    source = load_dataset(name, low_memory=False)
    before = source.copy(deep=True)
    output = upsample_df(source, "keep_remove_label")
    repeated = upsample_df(source, "keep_remove_label")
    assert len(output) == rows
    assert output["keep_remove_label"].value_counts().sort_index().to_dict() == counts
    assert list(output.columns) == list(source.columns)
    assert output.dtypes.equals(source.dtypes)
    assert output.iloc[: len(source)].reset_index(drop=True).equals(source.reset_index(drop=True))
    assert source.equals(before)
    assert output.equals(repeated)
    print(name, len(output), counts)
PY
```

Expected output:

```text
STUDY_2_KEEP_REMOVE_LABELS 30280 {0: 15140, 1: 15140}
STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS 7486 {0: 3743, 1: 3743}
STUDY_2_KEEP_REMOVE_SPLIT_LABELS 14562 {0: 7281, 1: 7281}
```

Inspect and commit only this implementation unit:

```bash
git diff --check -- shared/utils/upsample.py
git diff --name-only -- shared/utils/upsample.py
git add shared/utils/upsample.py
git commit -m "Implement deterministic DataFrame upsampling"
```

Expected output: the first command prints nothing. The second command lists only `shared/utils/upsample.py`. Git creates one commit named `Implement deterministic DataFrame upsampling` containing only that file.

## Pass

- The live data command prints the three exact balanced counts and confirms repeatability.
- Every output retains the source columns, dtypes, and original row prefix.
- Every source DataFrame remains unchanged.
- The commit changes one production file.

## Fail

- Any count differs from the expected output.
- Input order, columns, dtypes, or values change outside sampled additions.
- Null labels are sampled or dropped instead of rejected.
- The helper mutates its input.
- The writer or registry changes in this commit.
