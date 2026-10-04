# Step 1: Scaffold the shared helper and Study 2 caller

## Goal

Create the importable file structure and a thin caller that shows the full local generation path. Do not implement sampling, validation, dataset loading, path resolution, directory creation, CSV writing, or console reporting in this step.

## Scope

- **Plan input:** `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/proposal.md`
- **Main caller:** `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py::main`
- **Happy path:** load each registered source, balance it through the shared helper, resolve the registered output path, and write the CSV.
- **Unit of work:** importable scaffolding for that one caller path.
- **Out of scope:** contracts, registry entries, sampling behavior, S3 writes, data generation, and documentation changes.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/transform.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/utils/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/shared/utils/upsample.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/upsample_keep_remove_labels.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/transform.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/split_keep_remove_labels.py`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- Every file under `/Users/mark/src/work/mirrorview-wt/data_platform/` and `/Users/mark/src/work/mirrorview-wt/experiments/`

## Exact scaffold

Create this tree:

```text
/Users/mark/src/work/mirrorview-wt/shared/
  utils/
    __init__.py
    upsample.py
  data/
    transformed/
      study_2/
        upsample_keep_remove_labels.py
```

`shared/utils/__init__.py` is a package marker and does not re-export the helper. Both new Python modules start with `from __future__ import annotations`. `shared/utils/upsample.py` contains the typed public function stub. `upsample_keep_remove_labels.py` contains typed writer and `main` stubs, imports the helper and existing data modules, and states the order of calls without implementing them.

## Commands and expected output

Run the import gate from the repository root:

```bash
PYTHONPATH=. uv run python -c "from shared.utils.upsample import upsample_df; from shared.data.transformed.study_2.upsample_keep_remove_labels import main, write_upsampled_keep_remove_label_datasets; print('upsample-scaffold-ok')"
```

Expected output:

```text
upsample-scaffold-ok
```

Stage and inspect only the allowed paths:

```bash
git add shared/utils/__init__.py shared/utils/upsample.py shared/data/transformed/study_2/upsample_keep_remove_labels.py
git diff --cached --check
git diff --cached --name-only
```

Expected output: `git diff --cached --check` prints nothing and exits zero. `git diff --cached --name-only` lists only the three scaffold files.

Commit only the scaffold:

```bash
git commit -m "Scaffold Study 2 upsample caller"
```

Expected output: Git creates one commit named `Scaffold Study 2 upsample caller` containing only the three allowed files.

## Pass

- The three scaffold files exist.
- Both public imports resolve.
- The caller shows load, balance, resolve, and write in that order.
- Every behavior body is `...` or raises `NotImplementedError`.
- The commit contains no registry changes or working behavior.

## Fail

- An import fails.
- Any business behavior exists in the scaffold.
- A file outside the allowed list changes.
- The scaffold and contracts are combined in one commit.
