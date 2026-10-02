# Step 5: Publish, document, and verify the datasets

## Goal

Prove the complete caller path, publish the three verified CSV files to their approved S3 keys, reload them through the registry, and document the result. Publish only after the local data checks pass.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_upsample_imbalanced_study_2_datasets_1bc9d4/plan.md`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md`
- `/Users/mark/src/work/mirrorview-wt/lib/aws/s3.py`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md`
- `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md`

The three ignored CSV files may be regenerated locally and uploaded. They must not be added to Git.

## Files forbidden to change

- Every Python file under `/Users/mark/src/work/mirrorview-wt/shared/`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- Every file under `/Users/mark/src/work/mirrorview-wt/data_platform/` and `/Users/mark/src/work/mirrorview-wt/experiments/`

If verification exposes a code defect, stop this step. Return to the owning implementation step, make one scoped fix commit, rerun its checks, and then restart Step 5.

## Verify before publication

Regenerate the local files:

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_2/upsample_keep_remove_labels.py
```

Expected output:

```text
wrote UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS rows=30280 counts={0: 15140, 1: 15140}
wrote UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS rows=7486 counts={0: 3743, 1: 3743}
wrote UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS rows=14562 counts={0: 7281, 1: 7281}
```

Check the local schema, counts, repeated IDs, and source coverage:

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

## Publish without replacing existing objects

Copy the lab credentials into the standard AWS variable names without printing either secret:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity --query 'Account' --output text
```

Expected output:

```text
517478598677
```

Stop if identity lookup fails or the account differs.

Confirm that all three target keys are absent. Use `S3.object_exists` so permission and connection errors stop the check instead of appearing to be missing keys:

```bash
PYTHONPATH=. uv run python - <<'PY'
from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from shared.data.dataloader import STUDY_DATA_BUCKET

keys = (
    "shared/data/transformed/study_2/upsampled_keep_remove_labels.csv",
    "shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv",
    "shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv",
)
store = S3(STUDY_DATA_BUCKET, region_name=DEFAULT_REGION_NAME)
existing = [key for key in keys if store.object_exists(key)]
if existing:
    raise SystemExit(f"refusing to replace existing keys: {existing}")
print("s3-targets-absent")
PY
```

Expected output:

```text
s3-targets-absent
```

Upload each file with a conditional create so a concurrent writer cannot be replaced:

```bash
PYTHONPATH=. uv run python - <<'PY'
from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from shared.data import registry
from shared.data.dataloader import STUDY_DATA_BUCKET
from shared.data.registry import (
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)

names = (
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
)
store = S3(STUDY_DATA_BUCKET, region_name=DEFAULT_REGION_NAME)
for name in names:
    entry = registry.get_dataset(name)
    local_path = registry.resolve_path(name)
    key = entry.relative_path.as_posix()
    store.upload_bytes(
        key,
        local_path.read_bytes(),
        content_type="text/csv",
        if_none_match="*",
    )
    print(f"uploaded=s3://{STUDY_DATA_BUCKET}/{key}")
PY
```

Expected output:

```text
uploaded=s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_labels.csv
uploaded=s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv
uploaded=s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv
```

If the command fails after a partial upload, do not delete or replace any object. Record which keys exist, compare their bytes to the local files, and ask for a recovery decision.

## Verify published bytes and registry loads

Compare local and remote SHA-256 digests:

```bash
for file in \
  upsampled_keep_remove_labels.csv \
  upsampled_keep_remove_unanimous_labels.csv \
  upsampled_keep_remove_split_labels.csv
do
  shasum -a 256 "shared/data/transformed/study_2/$file"
  aws s3 cp "s3://mirrorview-experimental-artifacts/shared/data/transformed/study_2/$file" - --region us-east-2 | shasum -a 256
done
```

Expected output: each local digest exactly matches the remote digest printed immediately after it.

Reload through the public data API:

```bash
PYTHONPATH=. uv run python -c "from shared.data.dataloader import load_dataset; from shared.data.registry import UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS; names=(UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS); print([(name, len(df), df['keep_remove_label'].value_counts().sort_index().to_dict()) for name in names for df in [load_dataset(name, low_memory=False)]])"
```

Expected output:

```text
[('UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS', 30280, {0: 15140, 1: 15140}), ('UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS', 7486, {0: 3743, 1: 3743}), ('UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS', 14562, {0: 7281, 1: 7281})]
```

## Document and close the implementation

Update `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_2/README.md` with:

- The registry name for each source and its output.
- The generation command.
- The fixed seed and repeated `post_id` behavior.
- The measured source and output class counts.
- The three S3 keys.

Add one concise entry to `/Users/mark/src/work/mirrorview-wt/CHANGELOG.md` that links issue 338 and names the three new registry datasets.

Run the final checks:

```bash
git diff --check
git check-ignore -v shared/data/transformed/study_2/upsampled_keep_remove_labels.csv shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv
git diff --name-only HEAD -- shared/data/transformed/study_2/README.md CHANGELOG.md
```

Expected output: `git diff --check` prints nothing. `git check-ignore` prints three matches for the `*.csv` rule. The final command lists only `CHANGELOG.md` and `shared/data/transformed/study_2/README.md`.

Commit the documentation:

```bash
git add CHANGELOG.md shared/data/transformed/study_2/README.md
git commit -m "Document balanced Study 2 datasets"
```

Expected output: Git creates one commit named `Document balanced Study 2 datasets` containing only the two documentation files.

## Pass

- The local checks print the exact approved counts, columns, and repeated ID counts.
- Conditional upload creates all three objects without replacing an existing object.
- Local and remote SHA-256 digests match for every file.
- `load_dataset` returns the exact balanced counts for all three new names.
- README and changelog describe the published data.
- Generated CSV files remain outside Git.

## Fail

- Local data differs from the approved counts or schema.
- AWS identity is unavailable or unapproved.
- Any target key exists before publication.
- A conditional upload, digest comparison, or registry load fails.
- Generated CSV files enter Git.
