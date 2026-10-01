# Proposal: Upsample three imbalanced Study 2 keep/remove datasets

Scope: [issue 338](https://github.com/METResearchGroup/mirrorView-task/issues/338). This proposal covers the shared DataFrame helper, the three derived Study 2 datasets, their registry entries, and their S3 objects. The source datasets created by [issue 325](https://github.com/METResearchGroup/mirrorView-task/issues/325) and [PR 328](https://github.com/METResearchGroup/mirrorView-task/pull/328) remain unchanged.

## Overview

Add `shared.utils.upsample.upsample_df` to make each value in one class column occur as often as the largest class. A Study 2 transform will apply the function to the all, unanimous, and split modal keep/remove tables. The transform will write three registered CSV datasets whose S3 keys match their paths in the repository. The output tables retain the source schema and contain repeated `post_id` values for rows sampled with replacement.

## Cross-cutting concerns

### Upsampling contract

`upsample_df(df, class_label, *, random_state=1)` treats `class_label` as a column name. The function retains each input row once and samples each smaller class with replacement until it matches the largest class. It appends the sampled rows without shuffling the original rows. The fixed seed makes regenerated CSVs reproducible.

The helper supports two or more classes. It returns a copy when the input is empty, contains one class, or is already balanced. A missing class column raises `KeyError`. A null class value raises `ValueError` because null is not a valid training label.

The helper uses `pandas.DataFrame.sample`, so the existing `pandas>=3.0.2` dependency is sufficient. It does not add a dependency on scikit-learn.

### Source datasets

The transform reuses the three existing registry entries and `shared.data.dataloader.load_dataset`:

| Source registry name | Rows measured on October 1, 2026 | Class counts measured from `keep_remove_label` | Scope |
| --- | ---: | --- | --- |
| `STUDY_2_KEEP_REMOVE_LABELS` | 20,000 | keep `15,140`; remove `4,860` | Every row with a modal label, including rows with 3 through 14 raters. |
| `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | 4,051 | keep `3,743`; remove `308` | Rows with five labelers and 0 or 5 remove votes. |
| `STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | 9,941 | keep `7,281`; remove `2,660` | Rows with five labelers and 1 through 4 remove votes. |

I measured the counts by loading the three current S3 objects through `load_dataset`. `upsample_keep_remove_labels.py` will use the existing unanimous and split datasets, so it will not repeat the filters in `build_unanimous_keep_remove_labels` and `build_split_keep_remove_labels`.

### Duplicate identities

Upsampling adds exact copies of rows from the smaller class. `post_id` therefore stops being unique in each output, while all 13 source columns remain unchanged. The outputs do not add a synthetic identifier or a column that counts repeats because either change would give callers a new schema to handle.

### Storage and registry

`shared.data.registry.DATASETS` remains the authoritative map from a dataset name to its CSV path in the repository. `shared.data.dataloader.load_dataset` will download each new object from `mirrorview-experimental-artifacts` without changing it.

Git will continue to ignore the generated CSV files under the existing `*.csv` rule. The implementation will upload the files to the registry paths in S3 and commit only Python and Markdown files.

## File structure

### Repository

```text
CHANGELOG.md

shared/
  utils/
    __init__.py                         package marker
    upsample.py                         deterministic DataFrame upsampling
  data/
    registry.py                         three UPSAMPLED_* names and DatasetEntry values
    transformed/
      study_2/
        README.md                       generation and registry documentation
        upsample_keep_remove_labels.py  loads, upsamples, and writes all three tables
```

The existing `transform.py` and `split_keep_remove_labels.py` stay unchanged.

### S3

```text
s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/
  upsampled_keep_remove_labels.csv
  upsampled_keep_remove_unanimous_labels.csv
  upsampled_keep_remove_split_labels.csv
```

## Schema and key interfaces

| Interface | Lives in | Role |
| --- | --- | --- |
| `upsample_df(df: pd.DataFrame, class_label: str, *, random_state: int = 1) -> pd.DataFrame` | `shared/utils/upsample.py` (**new**) | Samples every smaller class with replacement until it has the same row count as the largest class. |
| `write_upsampled_keep_remove_label_datasets() -> dict[str, pd.DataFrame]` | `shared/data/transformed/study_2/upsample_keep_remove_labels.py` (**new**) | Loads the three source tables, calls `upsample_df`, and writes each output to its registry path for upload. |
| `DatasetEntry` | `shared/data/registry.py` (**reused**) | Maps each new registry name to an S3 object key. |

Each output retains these existing fields: `post_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`, `n_raters`, `keep_rate`, `n_keep`, `n_remove`, `is_unanimous`, `sampled_stance`, `sample_toxicity_type`, and `platform`. The transform stores all fields in each CSV. It introduces no model that exists only in memory.

The new registry names are:

- `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS`
- `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`
- `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`

## Steps

### Step 1: Add the shared upsampling helper

Create `shared/utils/upsample.py` with the deterministic contract above. The helper will support more than two classes, and it will not import the Study 2 schema or storage code.

### Step 2: Build and register the three Study 2 datasets

Create one Study 2 transform that loops over the existing all, unanimous, and split registry names. For each table, it calls `upsample_df(..., "keep_remove_label")` and writes the new registry path. Add the three names and `DatasetEntry` values to `shared/data/registry.py`.

### Step 3: Publish and document the outputs

Upload the three CSVs to `mirrorview-experimental-artifacts` at their registry keys. Document which source produces each output, how repeated rows work, and the measured row counts in the Study 2 data README and changelog.

## Expected results

The following estimates come from the measured October 1, 2026 source counts. A pandas prototype that ran only in memory produced the same row and class counts and preserved every source column.

| New registry name | Output rows | Keep rows | Remove rows | Added sampled rows |
| --- | ---: | ---: | ---: | ---: |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS` | 30,280 | 15,140 | 15,140 | 10,280 |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | 7,486 | 3,743 | 3,743 | 3,435 |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | 14,562 | 7,281 | 7,281 | 4,621 |

The transform makes no model or paid API calls, so token use and service cost are zero. Runtime and CSV byte sizes have not been measured. The implementation run can record them if the data README needs them.

## Confirmed decisions

The user confirmed all four decisions on October 1, 2026.

1. **Confirmed: use `class_label` as the class column name and default `random_state` to `1`.** This matches issue 338 and gives callers the same sampled rows without requiring a seed on every call.
2. **Confirmed: upsample all 20,000 rows in `STUDY_2_KEEP_REMOVE_LABELS`.** The issue names the registry entry that contains all modal labels, while only the unanimous and split source datasets are limited to five labelers.
3. **Confirmed: keep all 13 source columns unchanged.** Repeated `post_id` values record the sampled rows without adding a synthetic row ID or repeat count.
4. **Confirmed: store ignored CSVs only in S3 under the registry paths.** This follows PR 328 and keeps generated data out of Git.
