# Step 1: Upload the pinned csv and write the inventory

## Scope

- **Caller:** `data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` `main`, then `data_platform/scripts/verify_twitter_preprocessed_s3.py` `main`.
- **Task:** Copy the single pinned Twitter `posts.csv` to S3 at the repo-relative key, refuse Git LFS pointer text, hash with SHA-256 of full object bytes, write the inventory JSON, and verify the remote object.
- **Out of scope:** Campaign YAML, Twitter campaign CLI, smoke, watcher, labeling 6,374 rows, converting csv to parquet, dropping Git LFS, uploading Bluesky or Reddit paths, pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py` (upload, LFS pull, pointer rejection, SHA-256, inventory writer)
- `/workspace/data_platform/scripts/verify_bluesky_s3_migration.py` (re-download and compare SHA-256, never ETag)
- `/workspace/lib/aws/s3.py` (`upload_bytes`, `get_bytes`)
- `/workspace/lib/timestamp_utils.py` (`get_current_timestamp`)
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json` (must stay `format: csv`)
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/metadata.json` (row count 6374)
- `/workspace/.gitattributes` (Twitter csv LFS rule; do not edit)

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` (new)
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py` (new)
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` (new, after a successful upload)

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/**`
- `/workspace/data_platform/data/bluesky/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Locked identities

| Field | Value |
|-------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Upload scope | `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv` |
| Object count | `1` |
| Hash | SHA-256 lowercase hex of full object bytes. Never use S3 ETag as a content hash. |
| Inventory path | `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` |

Primary S3 object:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv`

Inventory JSON shape:

```json
{
  "bucket": "mirrorview-experimental-artifacts",
  "region": "us-east-2",
  "dataset_id": "twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547",
  "preprocessed_run": "2026_09_06-19:28:47",
  "uploaded_at": "<UTC from lib.timestamp_utils.get_current_timestamp>",
  "object_count": 1,
  "objects": [
    {
      "repo_relative_path": "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv",
      "s3_key": "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv",
      "bytes": 2584416,
      "sha256": "<lowercase hex of full object bytes>"
    }
  ]
}
```

`bytes` must be the actual file length after a successful LFS pull. The size 2584416 is the expected nearby value, not a value to hard-code if the live file differs.

## Work

Copy the Bluesky migrate and verify scripts. Change them to one path.

1. `run_git_lfs_pull` with include pattern `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv`.
2. `read_scoped_bytes` aborts with `ValueError` if the file begins with `version https://git-lfs.github.com/spec/v1`.
3. Upload with key equal to the repo-relative path. Re-download. Compare length and SHA-256. Never use ETag.
4. Refuse a key that starts with `data_platform/data_platform/`.
5. Write inventory after a successful upload. Include `preprocessed_run`.
6. Verifier loads the inventory, checks bucket, region, `object_count == 1`, re-downloads, and compares SHA-256.

Content type for non-json follows `migrate_bluesky_lfs_to_s3.py` (`application/octet-stream`).

## Contracts (implement-from-spec Phase 3)

- `BUCKET = "mirrorview-experimental-artifacts"`
- `REGION = "us-east-2"`
- `EXPECTED_OBJECT_COUNT = 1`
- `LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"`
- Inventory includes `preprocessed_run`.
- Hash helper is SHA-256 of full bytes.

## Given / when / then (Phase 4, no pytest)

```text
given AWS credentials exported from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
when aws sts get-caller-identity
then exit 0 and JSON Arn contains the lab IAM user

given the Twitter posts.csv Git LFS pointer in the working tree
when git lfs pull --include "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv"
then the file is larger than 2000 bytes and does not start with the LFS pointer header
and printed size is near 2584416

given the smudged csv on disk
when PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
then stdout contains "uploaded 1 object"
and the inventory lists one object at the repo-relative key
and that object's sha256 is the SHA-256 of the local file bytes

given the written inventory
when PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
then stdout is "OK: 1/1 objects present with matching sha256"

given git LFS tracking for the Twitter dataset csv files
when git lfs ls-files | grep "twitter_fba4ddb2" | grep "posts.csv"
then the preprocessed posts.csv line remains
```

## Must pass

From the repo root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
git lfs pull --include "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv"
python3 -c "
from pathlib import Path
p = Path('data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv')
head = p.read_bytes()[:40]
assert not head.startswith(b'version https://git-lfs.github.com/spec/v1'), head
assert p.stat().st_size > 2000, p.stat().st_size
print('csv smudged ok', p.stat().st_size)
"
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
git lfs ls-files | grep "twitter_fba4ddb2" | grep "posts.csv"
```

Expected:

- `csv smudged ok` plus a byte size near 2584416
- migrate reports `uploaded 1 object`
- verifier prints `OK: 1/1 objects present with matching sha256`
- `git lfs ls-files` still lists the preprocessed `posts.csv`

Copy migrate and verify stdout to `/opt/cursor/artifacts/`.

Commit the inventory only after verify succeeds.

## Must fail

- Using S3 ETag as the content hash
- Uploading while the local file is still an LFS pointer
- An S3 key that starts with `data_platform/data_platform/`
- Inventory rows for raw Twitter csv, `metadata.json`, Bluesky paths, or Reddit paths
- Removing the Git LFS pointer from git

## Done when

The scoped csv exists in S3 with a matching inventory SHA-256. Git still tracks the csv as LFS. No pytest was added or run.
