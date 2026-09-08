# Step 1: Add the experiment folder and load the pinned curated file

## Goal

Operators need a local experiment command that can read the pinned curated Reddit parquet without changing it, so this step adds `experiments/reddit_curated_perspective_v2_2026_09_08/` and a load path that downloads that object, checks row counts, and lists the medium comments that Step 2 will score.

## Dependencies

No earlier experiment step. The curated source must already exist from the Reddit LLM campaign consolidate, which landed in PR #258.

## Scope

- Caller: `experiments/reddit_curated_perspective_v2_2026_09_08/run.py` → `load_pinned_curated()` then `main()` with `--load-only`
- Slice: download pinned parquet → hash check → row and medium-count check → write a local medium-id list
- Out of scope: Perspective scoring, ranking, writing `mirrorview_v2.parquet`, product feature generation, curation YAML edits

## Pinned identities

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Curated run | `2026_09_07-21:47:32` |
| Source object | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview.parquet` |
| Source S3 key | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview.parquet` |
| Source SHA-256 of bytes | `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f` |
| Expected rows | 43061 |
| Expected medium rows | 20727 |
| Toxicity column | `llm_toxicity_tier` |
| Medium value | `medium` |
| Id column | `source_record_id` |
| Text column | `text` |
| Region | `us-east-2` |

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/wide_run_report.md` | Pinned curated URI, hash, 43061 rows, 20727 medium |
| `data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore.get` and `parse_s3_uri` |
| `data_platform/utils/object_store.py` | `DEFAULT_S3_BUCKET`, `DEFAULT_S3_REGION`, `sha256_hex` |
| `data_platform/curate/consolidate_reddit_llm_campaign.py` | How the campaign downloaded parquet and hashed bytes |
| `experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py` | Experiment folder layout and `PYTHONPATH=.` caller |
| `lib/constants.py` | `REPO_ROOT` |

## Files allowed to change

- `experiments/reddit_curated_perspective_v2_2026_09_08/run.py` (create)
- `experiments/reddit_curated_perspective_v2_2026_09_08/load_curated.py` (create)
- `experiments/reddit_curated_perspective_v2_2026_09_08/README.md` (create)
- `tests/experiments/test_reddit_curated_perspective_v2.py` (create)
- `docs/plans/2026-09-08_reddit_curated_perspective_d2_d56b10/` (already on the branch)

## Files forbidden to change

- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `data_platform/curate/configs/reddit/mirrorview.yaml`
- `data_platform/curate/consolidate_reddit_llm_campaign.py`
- The S3 object `.../curated/2026_09_07-21:47:32/mirrorview.parquet`
- `CHANGELOG.md` until the experiment has actually run and the v2 object exists

## Contracts to lock

```text
PINNED_CURATED_S3_URI = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/reddit/"
    "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/"
    "mirrorview.parquet"
)
PINNED_CURATED_SHA256 = "1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f"
EXPECTED_CURATED_ROW_COUNT = 43061
EXPECTED_MEDIUM_ROW_COUNT = 20727
LLM_TOXICITY_TIER_COLUMN = "llm_toxicity_tier"
MEDIUM_TIER = "medium"
SOURCE_RECORD_ID_COLUMN = "source_record_id"
TEXT_COLUMN = "text"

def load_pinned_curated(
    *,
    store: CampaignObjectStore | None = None,
    cache_path: Path | None = None,
) -> pd.DataFrame

def medium_rows(curated: pd.DataFrame) -> pd.DataFrame
```

`load_pinned_curated` downloads the pinned object when `cache_path` is missing or the cached bytes do not match `PINNED_CURATED_SHA256`. It hashes the downloaded bytes with `sha256_hex` / the same file hasher the consolidate script uses. A hash mismatch raises `ValueError` and does not write S3.

After a successful load, row count must equal 43061. `medium_rows` keeps rows where `llm_toxicity_tier == "medium"`. That subset must have 20727 rows and 20727 distinct `source_record_id` values. Empty `text` after strip raises `ValueError`.

The cache file lives under `experiments/reddit_curated_perspective_v2_2026_09_08/cache/` and is gitignored. The command never calls `CampaignObjectStore.put_new` or `replace` on the pinned source key.

`--load-only` stdout includes:

```text
curated_rows=43061
medium_rows=20727
source_sha256=1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f
```

AWS credentials use the default chain after:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

## Test design

Do not call S3 or Perspective in unit tests. Pass a tiny in-memory frame, or a fake store whose `get` returns known parquet bytes.

```text
given a 3-row frame with llm_toxicity_tier low, medium, high
when medium_rows(frame)
then 1 row remains
and that row's llm_toxicity_tier is medium

given load_pinned_curated with a fake store whose body hashes to PINNED_CURATED_SHA256
and the parquet has 43061 rows and 20727 medium
when load_pinned_curated()
then the frame has 43061 rows

given a fake store body whose hash is not PINNED_CURATED_SHA256
when load_pinned_curated()
then ValueError
and put_new was not called

given a frame with 43061 rows but 20726 medium
when the load checks run
then ValueError
```

A fixture parquet with 43061 rows is too large for git. Prefer a injectable expected-count parameter in tests, with production constants as the CLI defaults. Production `run.py --load-only` still checks 43061 and 20727.

## Implementation notes (implement-from-spec)

Full auto. One Git commit per phase that changes the repo.

1. Phase 1 scope. Confirm caller and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Create `load_curated.py` and `run.py` with stubs that raise `NotImplementedError`. Create `README.md` with the `--load-only` command only.
3. Phase 3 contracts. Lock constants and function signatures. Bodies stay stubs.
4. Phase 4 tests. Add `tests/experiments/test_reddit_curated_perspective_v2.py` for the load and medium-filter cases. Tests fail on `NotImplementedError`.
5. Phase 5 units, one commit each:
   1. Implement `medium_rows`.
   2. Implement `load_pinned_curated` hash and count checks, including fake-store tests.
   3. Wire `--load-only` in `run.py` and fill the README load section.
6. Phase 6. Run the must-pass pytest command. Then run live `--load-only` against S3 and confirm the three stdout lines. Do not upload anything.

Do not add `__init__.py` under the experiment folder unless pytest import requires it. Prefer importing `experiments.reddit_curated_perspective_v2_2026_09_08.load_curated` if the folder name is a valid module. If the date folder is awkward as a package, keep scripts importable via `sys.path` from `run.py` and import helpers in tests from a stable module path documented in the test file.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/experiments/test_reddit_curated_perspective_v2.py -q
```

Expected: exit 0 for the Step 1 tests. Step 2 and Step 3 tests may still be absent.

Live load, after AWS exports:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
```

Expected stdout includes `curated_rows=43061`, `medium_rows=20727`, and the pinned SHA-256. Exit 0.

## Must fail / not happen

- Any write to the pinned `mirrorview.parquet` object.
- Scoring or v2 upload in this step.
- Edits to `FEATURE_REGISTRY` or `mirrorview.yaml`.
- Live S3 calls inside unit tests.
