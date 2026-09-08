# Step 2: Run live smoke and commit the inventory

## Scope

- **Caller:** same migrate and verify `main` functions from Step 1, run from the repo root with lab AWS credentials.
- **Task:** Pull the scoped LFS blob, upload the one comments parquet, commit `s3_preprocessed_inventory.json`, and run every live smoke command below.
- **Out of scope:** Script design (Step 1), changelog until the pull request exists, pytest, edits to pipeline storage.

## Files to inspect

- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py`
- `data_platform/scripts/verify_reddit_preprocessed_s3.py`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet`

## Files allowed to change

- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json` (new, after successful upload)
- Temporary files under `experiments/reddit_s3_preprocessed_smoke_2026_09_07/` during review only. Delete that directory before the last product commit.

## Files forbidden to change

- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` except for a correctness bug found during smoke
- `data_platform/scripts/verify_reddit_preprocessed_s3.py` except for a correctness bug found during smoke
- `data_platform/utils/storage.py`
- `lib/aws/s3.py`
- `.gitattributes`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/**`
- `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/**`
- `data_platform/data/bluesky/**`
- `CHANGELOG.md` (until after the pull request exists)
- Any file under `tests/`

## Live smoke (must actually run)

From the repo root. Never print secrets.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
git lfs pull --include "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet"
python3 -c "from pathlib import Path; p=Path('data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet'); head=p.read_bytes()[:4]; assert head==b'PAR1', head; print('parquet magic ok', p.stat().st_size)"
PYTHONPATH=. uv run python data_platform/scripts/migrate_reddit_preprocessed_to_s3.py
PYTHONPATH=. uv run python data_platform/scripts/verify_reddit_preprocessed_s3.py
aws s3api head-object --bucket mirrorview-experimental-artifacts --key data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet --region us-east-2
git lfs ls-files | grep reddit_3d8a2c41 | grep comments.parquet
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
inv = json.loads(Path("data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json").read_text())
assert inv["object_count"] == 1
assert len(inv["objects"]) == 1
assert inv["objects"][0]["s3_key"].startswith("data_platform/")
assert "data_platform/data_platform/" not in inv["objects"][0]["s3_key"]
assert inv["preprocessed_run"] == "2026_09_03-23:39:28"
print("inventory ok", inv["uploaded_at"])
PY
```

## Expected results

- `aws sts get-caller-identity` exits 0 and prints JSON with an `Arn`.
- `git lfs pull` exits 0.
- `parquet magic ok` plus a byte size well above 200.
- Migrate stdout ends with `uploaded 1 object to s3://mirrorview-experimental-artifacts/` and exit code 0.
- Verify stdout is `OK: 1/1 objects present with matching sha256` and exit code 0.
- `head-object` returns HTTP 200 metadata with non-zero `ContentLength`.
- `git lfs ls-files` shows one line for the preprocessed comments parquet.
- Inventory check prints `inventory ok` plus a timestamp.

## Must fail

- Verification that accepts ETag instead of SHA-256.
- Upload of LFS pointer text (about 133 bytes).
- Object count other than 1.
- S3 key starting with `data_platform/data_platform/`.
- Bluesky paths, Reddit raw paths, or `dataset.json` in the inventory.
- Git LFS pointer removed or rewritten.
- Any automated test file added or run.

## Done when

The inventory JSON is committed. All live smoke commands above pass. The temporary smoke directory is gone if it was created. The parquet remains an LFS pointer.
