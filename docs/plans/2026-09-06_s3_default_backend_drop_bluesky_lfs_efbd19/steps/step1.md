# Step 1: Pin tests to local disk, flip the default backend to S3, and untrack the pinned Bluesky parquet files

## Goal

Make `resolve_object_store` return the S3 store when `DATA_PLATFORM_STORAGE_BACKEND` is unset, keep `local` as the explicit override, and remove the 25 parquet files of the pinned Bluesky dataset from git and Git LFS tracking. Keep the four JSON manifests tracked. Make sure no test can reach the production bucket before the default changes.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step3.md`. Every locked value below is copied from it, plus one amendment from the epic manager: `tests/data_platform/conftest.py` may change for a fixture-only edit with no new test cases. If the two files disagree on anything else, the epic step spec wins and this file is wrong.

## Main caller

`data_platform/utils/storage.py` `StorageManager.__init__`, which calls `data_platform/utils/object_store.py` `resolve_object_store(local_root=DATA_ROOT)`.

Happy path through the caller: read `DATA_PLATFORM_STORAGE_BACKEND`, treat an unset value as `s3`, read `DATA_PLATFORM_S3_BUCKET` with its default, and return an `S3ObjectStore`. `load_records(latest=True)` then downloads the pinned `posts.parquet` and returns 200,000 rows.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step3.md` | Locked contracts, smoke commands, forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Bucket, region, and prefix shared by later steps |
| `data_platform/utils/storage.py` | `StorageManager.__init__` calls `resolve_object_store`; `latest_run_dir` still lists the local run directory |
| `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` | The 53 S3 keys and hashes; 28 of them sit under `data_platform/data/` |
| `data_platform/scripts/verify_bluesky_s3_migration.py` | Post-change inventory check |
| `tests/data_platform/utils/conftest.py` | The `bluesky_storage` fixture builds a `BlueskyStorageManager` and must keep working |
| `AGENTS.md` | `PYTHONPATH=.` and AWS credential export pattern |

## Files allowed to change

- `data_platform/utils/object_store.py` (default backend flip and the two docstrings that state the default; nothing else)
- `tests/data_platform/conftest.py` (one autouse fixture; no new test cases)
- `.gitattributes` (delete the Bluesky pipeline parquet LFS line only)
- `.gitignore` (replace the pinned Bluesky dataset un-ignore lines so only JSON manifests stay tracked)
- Git index only, for removal from tracking of the 25 parquet files under `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/`

`CHANGELOG.md` is edited only in a separate commit after implementation. No smoke artifacts are committed; smoke output goes into the PR description.

## Files forbidden to change

- `data_platform/utils/storage.py` (its class docstring still says local disk is the default; the epic step spec does not allow this file, so leave it and note it in the PR)
- `data_platform/scripts/migrate_bluesky_lfs_to_s3.py`
- `data_platform/scripts/verify_bluesky_s3_migration.py`
- `data_platform/ingestion/data_dumps/bluesky/data/**` (dump LFS stays)
- `data_platform/data/reddit/**`
- `.gitattributes` lines for Reddit or dump parquet
- `data_platform/generate_features/**`, `data_platform/preprocessing/**`, `data_platform/ingestion/sync_bluesky.py`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json`, both `metadata.json` files, and `s3_migration_inventory.json` (content stays; they remain tracked)
- Any file under `tests/` other than `tests/data_platform/conftest.py`
- Any file under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/`, `docs/plans/2026-09-05_copy_bluesky_lfs_artifacts_to_s3_9877d3/`, or `docs/plans/2026-09-05_s3_object_store_storage_backend_d13173/`
- Any git history rewrite (`git filter-repo`, `git lfs migrate`, force push, amend of a pushed commit)
- Any S3 write or delete

Stage files by explicit path only. Never run `git add -A` or `git add .`. `git status` lists the pulled parquet files as modified even though `git diff` is empty; `git rm --cached` on those exact paths is the only index operation that touches them.

## Locked values

| Item | Value |
|------|-------|
| Production default backend | `s3` when `DATA_PLATFORM_STORAGE_BACKEND` is unset |
| Local override | `DATA_PLATFORM_STORAGE_BACKEND=local` |
| Invalid backend value | Still raises `ValueError` |
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| S3 key prefix | `data_platform/data/` |
| Test backend pin | Autouse fixture sets `DATA_PLATFORM_STORAGE_BACKEND=local` and `DATA_PLATFORM_S3_BUCKET=mirrorview-tests-must-not-touch-s3` for every test under `tests/data_platform/` |
| Parquet removed from git | Exactly 25 files: 24 under `raw/2026_09_01-00:00:00/date=2026-09-01/hour=*/` and `preprocessed/2026_09_03-23:51:30/posts.parquet` |
| JSON kept in git | `dataset.json`, `raw/2026_09_01-00:00:00/metadata.json`, `preprocessed/2026_09_03-23:51:30/metadata.json`, `s3_migration_inventory.json` |
| `.gitattributes` change | Delete the line `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet filter=lfs diff=lfs merge=lfs -text` |
| Dump LFS untouched | `data_platform/ingestion/data_dumps/bluesky/data/parquet/**` remains LFS |
| Reddit LFS untouched | All `data_platform/data/reddit/**` rules and files unchanged |
| Directory placeholder | The tracked `dataset.json` and the two `metadata.json` files keep every needed directory in git, so no `.gitkeep` is added |
| History | No force push, no LFS history rewrite, no `git filter-repo` |

## Contracts

`data_platform/utils/object_store.py`:

- `resolve_object_store(*, local_root: Path) -> ObjectStore` keeps its signature. The lookup becomes `os.environ.get(STORAGE_BACKEND_ENV_VAR, S3_BACKEND)`. `local` returns `LocalObjectStore(local_root)`, `s3` returns `S3ObjectStore(bucket)` with `bucket` from `DATA_PLATFORM_S3_BUCKET` or `DEFAULT_S3_BUCKET`, and any other value raises `ValueError`.
- The module docstring and the `resolve_object_store` docstring say that the variable defaults to S3.
- No other symbol changes.

`tests/data_platform/conftest.py`:

- Adds `local_storage_backend`, an autouse fixture that takes `monkeypatch` and sets `STORAGE_BACKEND_ENV_VAR` to `LOCAL_BACKEND` and `S3_BUCKET_ENV_VAR` to `mirrorview-tests-must-not-touch-s3`, importing those names from `data_platform.utils.object_store`. Its docstring states in one or two sentences that the production default is S3 and that the fake bucket keeps even a deliberate `s3` test away from the production bucket.
- The existing `data_root` fixture and helpers do not change.

`.gitignore`:

- The three lines under `data_platform/data/**` that un-ignore `data_platform/data/bluesky/`, the dataset directory, and the dataset directory `**` become lines that un-ignore `data_platform/data/bluesky/`, the dataset directory, every subdirectory of the dataset directory, and `*.json` at any depth under the dataset directory. Parquet files under the dataset directory fall back to the `data_platform/data/**` ignore rule. The Reddit lines directly below do not change.

`.gitattributes`:

- Only the Bluesky pipeline line is deleted. The file keeps the dump line, the Reddit dump line, and the Reddit pipeline line.

## Check design

No pytest files are added. The scenarios below are the executable spec, and each maps to one command in the next section. The autouse fixture is the only test change, and it lands before the default flips so no commit on the branch leaves the suite pointed at the production bucket.

```text
given AWS credentials and no DATA_PLATFORM_STORAGE_BACKEND
when BlueskyStorageManager(PREPROCESSED, dataset).load_records(latest=True)
then the dataframe has 200000 rows

given DATA_PLATFORM_STORAGE_BACKEND=local
when resolve_object_store(local_root=DATA_ROOT)
then a LocalObjectStore is returned

given the full test suite with the flipped default and AWS credentials stripped
when uv run pytest -q
then 631 passed and zero NoCredentialsError

given the full test suite with the flipped default and AWS credentials present
when uv run pytest -q and then a listing of s3://mirrorview-experimental-artifacts/data_platform/data/
then 631 passed and the listing equals the 28 inventory keys under that prefix

given the updated .gitignore and .gitattributes
when git lfs ls-files, git ls-files, and git check-ignore run on the dataset directory
then no LFS path under the dataset, no tracked parquet under the dataset, the four JSON files tracked and not ignored, and each parquet path ignored
```

## Ordered implementation work

1. Add the autouse fixture to `tests/data_platform/conftest.py`. Run `uv run pytest -q` and expect 631 passed. Commit.
2. Change the default in `resolve_object_store` to `S3_BACKEND` and update the two docstrings in `object_store.py`. Commit.
3. Delete the Bluesky pipeline line from `.gitattributes`, rewrite the pinned dataset un-ignore lines in `.gitignore`, and run `git rm --cached` on the 25 parquet paths. Stage `.gitattributes` and `.gitignore` by path. Confirm the four JSON files are still tracked. Commit.
4. Run every command in the next section.

## Live smoke and basic check commands

Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**Default backend is S3**

```bash
unset DATA_PLATFORM_STORAGE_BACKEND
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
storage = BlueskyStorageManager(StorageStage.PREPROCESSED, "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73")
df = storage.load_records(latest=True)
assert len(df) == 200000
print("default s3 backend ok", len(df))
PY
```

Expected stdout: `default s3 backend ok 200000`, exit code 0.

**Local override still works**

```bash
DATA_PLATFORM_STORAGE_BACKEND=local \
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import DATA_ROOT
from data_platform.utils.object_store import resolve_object_store
assert resolve_object_store(local_root=DATA_ROOT).__class__.__name__ == "LocalObjectStore"
print("local override ok")
PY
```

Expected stdout: `local override ok`.

**Migration inventory still valid**

```bash
PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
```

Expected stdout: `OK: 53/53 objects present with matching sha256`.

**No Bluesky pipeline parquet in LFS or in git**

```bash
git lfs ls-files | grep "data_platform/data/bluesky/bluesky_7e2c4a91" || echo "no bluesky pipeline lfs"
git ls-files "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet" | wc -l
```

Expected stdout: `no bluesky pipeline lfs` and then `0`.

**JSON manifests still tracked and not ignored**

```bash
git ls-files "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/*.json" "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/metadata.json"
for f in $(git ls-files data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 | grep '\.json$'); do git check-ignore -q --no-index "$f" && echo "IGNORED $f" || echo "not ignored $f"; done
```

Expected stdout: the four JSON paths (`dataset.json`, `s3_migration_inventory.json`, and both `metadata.json`) from the first command, then four `not ignored` lines and no `IGNORED` line. `check-ignore -q` exits 0 only when a path is ignored, so `--no-index` makes the rule check apply to tracked files too.

**Parquet paths are ignored on disk**

```bash
git check-ignore -q data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet && echo "parquet ignored"
git status --short data_platform/data/bluesky/ | wc -l
```

Expected stdout: `parquet ignored` and then `0`.

**Dump and Reddit LFS unchanged**

```bash
git lfs ls-files | grep -E "data_dumps/bluesky|data/reddit" | wc -l
git diff cursor/epic-180-182-s3-storage-support-d983...HEAD -- .gitattributes
```

Expected: `27`, and a diff that deletes only the one Bluesky pipeline line.

**Production safety check (a): suite with credentials stripped**

```bash
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN AWS_EC2_METADATA_DISABLED=true uv run pytest -q 2>&1 | tee /tmp/pytest_no_creds.txt | tail -1
grep -c NoCredentialsError /tmp/pytest_no_creds.txt
```

Expected: `631 passed` and then `0`.

**Production safety check (b): suite with credentials present**

```bash
uv run pytest -q | tail -1
```

Expected: `631 passed`.

**Production safety check (c): bucket listing unchanged after (b)**

```bash
PYTHONPATH=. uv run python - <<'PY'
import json, boto3
inventory = json.load(open("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json"))
expected = {o["s3_key"] for o in inventory["objects"] if o["s3_key"].startswith("data_platform/data/")}
s3 = boto3.client("s3", region_name="us-east-2")
keys = set()
for page in s3.get_paginator("list_objects_v2").paginate(Bucket="mirrorview-experimental-artifacts", Prefix="data_platform/data/"):
    keys.update(o["Key"] for o in page.get("Contents", []))
print("listed", len(keys), "expected", len(expected))
print("extra", sorted(keys - expected))
print("missing", sorted(expected - keys))
PY
```

Expected stdout: `listed 28 expected 28`, `extra []`, `missing []`. Any extra key means a test wrote to production. Stop and report it. Do not delete anything.

## Acceptance criteria

- The default backend smoke prints `default s3 backend ok 200000`.
- The local override smoke prints `local override ok`.
- The inventory check prints `OK: 53/53 objects present with matching sha256`.
- No path under the pinned dataset appears in `git lfs ls-files`, and no parquet under it appears in `git ls-files`.
- The four JSON files are tracked and not ignored; the parquet paths are ignored and `git status` is clean under `data_platform/data/bluesky/`.
- The dump and Reddit LFS count is 27 and the `.gitattributes` diff deletes one line.
- Safety checks (a), (b), and (c) pass with the expected output.

## Failure conditions

- Any pinned Bluesky parquet remains in `git lfs ls-files` or `git ls-files`.
- A JSON manifest is removed from git or becomes ignored.
- A Reddit or dump LFS rule changes.
- The default backend remains `local`, or the local override stops working.
- Any test reaches S3 without credentials, or any key appears in the bucket listing that is not in the inventory.
- Git history is rewritten or force-pushed.

## Commit rules

- Three implementation commits in the order above: fixture, default flip, git tracking changes.
- Stage files by explicit path. Never stage a parquet file.
- PR title: `Default data platform storage to S3 and drop Bluesky pipeline LFS`.
