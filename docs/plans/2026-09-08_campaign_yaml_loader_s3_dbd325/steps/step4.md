# Step 4: Copy posts.csv to S3 and write the inventory

## Scope

- **Caller:** `data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` `main`, then `data_platform/scripts/verify_twitter_preprocessed_s3.py` `main`.
- **Task:** Pull Git LFS bytes for the new preprocessed csv, upload that one object, write inventory under the new dataset, and verify SHA-256.
- **Out of scope:** Labeling 6408 rows, disposable smoke, primary `batches/part-*.parquet`, pytest, Bluesky, Reddit, raw csv, metadata upload.

## Files to inspect (read-only)

- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv`
- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py`
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py`
- `/workspace/AGENTS.md`

## Files allowed to change

- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/s3_preprocessed_inventory.json` (new)

## Files forbidden to change

- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/data_platform/data/bluesky/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- Any file under `/workspace/tests/`
- Any file outside the allowed list for this pull request

## Locked contracts

Upload only:

```text
s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv
```

Expected object count is 1. Hash is SHA-256 of object bytes. Never use S3 ETag. Abort if the local file still starts with Git LFS pointer text.

Storage for reading local dataset files:

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
```

AWS:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

Do not upload raw csv, metadata, Bluesky, or Reddit.

## Given / when / then (Phase 4, no new pytest)

```text
given the Git LFS preprocessed posts.csv for the new dataset
when the first 40 bytes are read
then they do not start with Git LFS pointer text
and file size is greater than 2000 bytes

given that smudged csv and AWS credentials
when migrate runs with --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2
     and --preprocessed-run 2026_09_08-01:48:08
then stdout includes uploaded 1 object

given the written inventory
when verify runs with the same flags
then stdout is OK: 1/1 objects present with matching sha256
```

## Exact commands and expected output

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
```

Expected: JSON with `"Arn"` containing the lab IAM user and exit 0.

```bash
git lfs pull --include "data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv"
python3 -c "
from pathlib import Path
p = Path('data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv')
head = p.read_bytes()[:40]
assert not head.startswith(b'version https://git-lfs.github.com/spec/v1'), head
assert p.stat().st_size > 2000, p.stat().st_size
print('csv smudged ok', p.stat().st_size)
"
```

Expected: `csv smudged ok` plus a byte size.

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08
```

Expected: migration reports `uploaded 1 object`. Verifier prints `OK: 1/1 objects present with matching sha256`.

Do not add pytest.

## Pass / fail

The step passes when one new `posts.csv` object is on S3 with matching SHA-256, inventory lives under the new dataset, and Git LFS still holds the local copy.

The step fails when any item below is true.

- migrate still pins the old csv when invoked for the new dataset
- raw csv, Bluesky, or Reddit objects were uploaded
- SHA-256 was taken from ETag
- LFS pointer text was uploaded
- official seven-feature production labeling started
- pytest was added
