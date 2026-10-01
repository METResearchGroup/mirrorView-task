# Step 2: Confirm contracts and register the outputs

## Goal

Define the approved function signatures, edge case behavior, caller boundaries, output order, and registry entries. Keep the helper and writer behavior stubbed. Approval of this plan package approves these contracts; any implementation change to them requires another review before behavior changes.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md`
- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/transform.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- Every file under `/Users/mark/src/work/mirrorview-wt/data_platform/` and `/Users/mark/src/work/mirrorview-wt/experiments/`

## Confirmed helper contract

`/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py` exposes exactly this public function:

```python
def upsample_df(
    df: pd.DataFrame,
    class_label: str,
    *,
    random_state: int = 1,
) -> pd.DataFrame:
    ...
```

The contract is:

1. `class_label` is a column name, not a class value or a pandas Series.
2. Every distinct class value that is not null has the row count of the largest input class in the output.
3. The function retains every input row once, in its original order.
4. The function appends sampled rows after the original rows. It processes smaller classes in the order in which they first appear.
5. Sampling uses replacement and the supplied `random_state`.
6. The output has a fresh `RangeIndex`, the same columns in the same order, and the same pandas dtypes as the input.
7. The input DataFrame is never modified.
8. Empty inputs, inputs with one class, and already balanced inputs return an independent copy with a fresh `RangeIndex`.
9. A missing `class_label` column raises `KeyError`.
10. Any null value in the class column raises `ValueError` before sampling.

Do not add a class, protocol, configuration model, scikit-learn dependency, shuffle option, or sampling strategy interface.

## Confirmed registry contract

Add these exact names and paths to `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`:

| Name | Relative path | Kind | Study phase |
| --- | --- | --- | --- |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS` | `shared/data/transformed/study_2/upsampled_keep_remove_labels.csv` | `transformed` | `study_2` |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | `shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv` | `transformed` | `study_2` |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | `shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv` | `transformed` | `study_2` |

Do not rename or modify an existing registry entry.

## Confirmed caller contract

`/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py` defines an ordered tuple of these source and output pairs:

1. `STUDY_2_KEEP_REMOVE_LABELS` to `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS`
2. `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` to `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`
3. `STUDY_2_KEEP_REMOVE_SPLIT_LABELS` to `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`

It exposes exactly this public writer:

```python
def write_upsampled_keep_remove_label_datasets() -> dict[str, pd.DataFrame]:
    ...
```

For each pair, the writer will:

1. Call `dataloader.load_dataset(source_name, low_memory=False)`.
2. Call `upsample_df(source, "keep_remove_label")`.
3. Call `registry.resolve_path(output_name)`.
4. Create the output parent directory.
5. Write CSV with `index=False`.
6. Add the result to the returned dictionary under the output registry name.

`main()` calls the writer and prints one line per output in the confirmed pair order. Each line includes the output registry name, absolute local path, total row count, and class counts sorted by class value. The command generates local files only. It does not upload, delete, or replace an S3 object.

## Commands and expected output

Run the contract import gate:

```bash
PYTHONPATH=. uv run python -c "from inspect import signature; from shared.utils.upsample import upsample_df; from shared.data.transformed.study_2.upsample_keep_remove_labels import write_upsampled_keep_remove_label_datasets; print(signature(upsample_df)); print(signature(write_upsampled_keep_remove_label_datasets))"
```

Expected output:

```text
(df: 'pd.DataFrame', class_label: 'str', *, random_state: 'int' = 1) -> 'pd.DataFrame'
() -> 'dict[str, pd.DataFrame]'
```

Run the registry gate:

```bash
PYTHONPATH=. uv run python -c "from shared.data.registry import DATASETS, UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS; names=(UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS); print([(name, DATASETS[name].relative_path.as_posix(), DATASETS[name].kind, DATASETS[name].study_phase) for name in names])"
```

Expected output:

```text
[('UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS', 'shared/data/transformed/study_2/upsampled_keep_remove_labels.csv', 'transformed', 'study_2'), ('UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS', 'shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv', 'transformed', 'study_2'), ('UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS', 'shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv', 'transformed', 'study_2')]
```

Commit the contracts separately:

```bash
git add shared/utils/upsample.py shared/data/registry.py shared/data/transformed/study_2/upsample_keep_remove_labels.py
git commit -m "Define Study 2 upsample contracts"
```

Expected output: Git creates one commit named `Define Study 2 upsample contracts` containing only the three allowed files.

## Pass

- The signatures and registry output match exactly.
- Docstrings state the return shape and exceptions.
- The helper and writer bodies still do not implement business behavior.
- Approval of this step is recorded before Step 3 begins.

## Fail

- A contract differs from the approved proposal or this step.
- A new dependency, abstraction, option, or schema field appears.
- Sampling or file writing behavior appears in the contracts commit.
- Any forbidden file changes.
