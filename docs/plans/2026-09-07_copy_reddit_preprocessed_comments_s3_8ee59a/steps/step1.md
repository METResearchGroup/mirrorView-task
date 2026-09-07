# Step 1: Add Reddit preprocessed migrate and verify scripts

## Scope

- **Caller:** `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` `main`, then `data_platform/scripts/verify_reddit_preprocessed_s3.py` `main`.
- **Task:** Add the two scripts that copy one pinned Reddit comments parquet to S3 and check SHA-256. Mirror `data_platform/scripts/migrate_bluesky_lfs_to_s3.py` and `data_platform/scripts/verify_bluesky_s3_migration.py`, cut down to one object.
- **Out of scope:** Live upload (Step 2), changelog, pipeline storage, Bluesky paths, pytest, edits to the epic plan under `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/`.

## Files to inspect

- `data_platform/scripts/migrate_bluesky_lfs_to_s3.py`
- `data_platform/scripts/verify_bluesky_s3_migration.py`
- `lib/aws/s3.py`
- `lib/constants.py`
- `lib/timestamp_utils.py`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/metadata.json`
- `.gitattributes`

## Files allowed to change

- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` (new)
- `data_platform/scripts/verify_reddit_preprocessed_s3.py` (new)

## Files forbidden to change

- `data_platform/utils/storage.py`
- `lib/aws/s3.py`
- `.gitattributes`
- `.gitignore`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/**`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/**`
- `data_platform/data/bluesky/**`
- `data_platform/ingestion/data_dumps/**`
- `CHANGELOG.md`
- Any file under `tests/`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/**`

## Locked identities

| Field | Value |
| ----- | ----- |
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Upload path | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet` |
| Inventory path | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json` |
| Expected object count | `1` |
| Content type | `application/octet-stream` |
| LFS pointer prefix | `version https://git-lfs.github.com/spec/v1` |

## Contracts

Inventory JSON shape:

```json
{
  "bucket": "mirrorview-experimental-artifacts",
  "region": "us-east-2",
  "dataset_id": "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079",
  "preprocessed_run": "2026_09_03-23:39:28",
  "uploaded_at": "<UTC from lib.timestamp_utils.get_current_timestamp>",
  "object_count": 1,
  "objects": [
    {
      "repo_relative_path": "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet",
      "s3_key": "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet",
      "bytes": 0,
      "sha256": "<lowercase hex of full bytes>"
    }
  ]
}
```

`uploaded_at` uses `lib.timestamp_utils.get_current_timestamp`. `bytes` is the real byte length after a successful upload. `sha256` is lowercase hex of full local bytes. Never use the S3 ETag as a content hash.

Migrate stdout ends like `uploaded 1 object to s3://mirrorview-experimental-artifacts/`.

Verifier stdout is `OK: 1/1 objects present with matching sha256`.

Keep functions under 20 lines. Use named constants, not magic numbers. Numpy docstrings. Module docstrings include the `uv run python ...` command.

Reuse `lib.aws.s3.S3` as-is: `upload_bytes` and `get_bytes`. Do not add `HeadObject` to the migrate hash path. Re-download is the content check.

## Ordered units of work

1. Named constants and the single frozen repo-relative path.
2. `run_git_lfs_pull` for the scoped include path.
3. `read_scoped_bytes` that aborts when the file still starts with the LFS pointer prefix.
4. `sha256_hex` of full bytes.
5. `upload_and_verify` that uploads with content type `application/octet-stream`, re-downloads, and compares length and SHA-256.
6. `write_inventory` that includes `preprocessed_run` and `object_count` 1.
7. Migrate `main`.
8. Verifier `verify_inventory` and `main` that import constants and `sha256_hex` from the migrate script.

Phase 4 for the epic is live smoke in Step 2, not pytest. Do not add files under `tests/`.

## Must pass (after scripts exist, before live upload)

```bash
PYTHONPATH=. uv run python -c "import data_platform.scripts.migrate_reddit_preprocessed_to_s3 as m; print(m.COMMENTS_PARQUET_RELATIVE_PATH); print(m.EXPECTED_OBJECT_COUNT)"
```

Expected: the locked repo-relative comments path on one line, then `1`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.scripts.verify_reddit_preprocessed_s3 import main; print(main.__name__)"
```

Expected: `main`.

## Must fail

- A migrate script that uploads `dataset.json`, `raw/**`, dumps, or Bluesky paths.
- A hash that uses S3 ETag.
- An S3 key that contains `data_platform/data_platform/`.
- Inventory without `preprocessed_run` or with `object_count` other than 1.
- Functions over 20 lines.

## Done when

Both scripts exist with contracts and stub-to-full behavior for the single-object path. Inventory file is not required until Step 2 succeeds.
