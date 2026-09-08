# Step 3: Write the v2 curated copy with 3000 promotions

## Goal

Operators need a second curated file in the same S3 folder, so this step ranks the 20727 scored medium comments, keeps the top 3000 by Perspective probability, copies the original curated table to `mirrorview_v2.parquet`, and changes only those 3000 LLM toxicity tiers from medium to high.

## Dependencies

Step 2 has a complete scores file with 20727 medium ids. The pinned `mirrorview.parquet` object is still at SHA-256 `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f`.

## Scope

- Caller: `experiments/reddit_curated_perspective_v2_2026_09_08/run.py` → `select_promotions()` then `write_curated_v2()` then `main()` with `--write-v2`
- Slice: rank → write 3000 ids → copy curated frame → set 3000 tiers to high → `put_new` v2 object → results report
- Out of scope: rescoring, changing the original curated object, changing `metadata.json`, changing MirrorView YAML, changing `FEATURE_REGISTRY`

## Pinned identities

| Field | Value |
|-------|-------|
| Promotion count | 3000 |
| Rank | `toxicity_prob` descending, then `source_record_id` ascending |
| v2 object | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` |
| v2 S3 key | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` |
| Write mode | `CampaignObjectStore.put_new` (fail if the v2 key already exists) |
| Promotion id file | `experiments/reddit_curated_perspective_v2_2026_09_08/outputs/promotion_source_record_ids.json` |
| Report | `experiments/reddit_curated_perspective_v2_2026_09_08/RESULTS.md` |

The original source stem is `mirrorview`. The v2 name is `mirrorview_v2.parquet`, which is `{name}_v2.parquet`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/generate_features/s3_feature_campaign.py` | `put_new` must not replace an existing object |
| `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/wide_run_report.md` | Original stance by LLM toxicity counts |
| `data_platform/utils/platform_specific_columns.py` | `STANDARDIZED_SOURCE_RECORD_ID_COLUMN` if the experiment should reuse the shared name |

## Files allowed to change

- `experiments/reddit_curated_perspective_v2_2026_09_08/promote_v2.py` (create)
- `experiments/reddit_curated_perspective_v2_2026_09_08/run.py`
- `experiments/reddit_curated_perspective_v2_2026_09_08/README.md`
- `experiments/reddit_curated_perspective_v2_2026_09_08/RESULTS.md` (create after the live write)
- `experiments/reddit_curated_perspective_v2_2026_09_08/outputs/promotion_source_record_ids.json`
- `tests/experiments/test_reddit_curated_perspective_v2.py`
- `CHANGELOG.md` (one 2026-09-08 operator line after the v2 object exists, in the same pull request as the live report)

## Files forbidden to change

- `data_platform/generate_features/registry.py`
- `data_platform/curate/configs/reddit/mirrorview.yaml`
- `data_platform/curate/consolidate_reddit_llm_campaign.py`
- The pinned `mirrorview.parquet` S3 object and `metadata.json` in that curated run folder
- Product feature campaign prefixes

## Contracts to lock

```text
PROMOTION_COUNT = 3000
V2_FILENAME = "mirrorview_v2.parquet"
HIGH_TIER = "high"

def select_promotions(
    scores: pd.DataFrame,
    *,
    count: int = PROMOTION_COUNT,
) -> list[str]
    sort toxicity_prob descending, source_record_id ascending
    return the first count source_record_id values as strings

def apply_promotions(
    curated: pd.DataFrame,
    promotion_ids: list[str],
) -> pd.DataFrame
    copy the frame
    for each promotion id, llm_toxicity_tier must currently be medium
    set those rows to high
    all other cells unchanged
    same columns, same row count, same row order as the input curated frame

def write_curated_v2(
    curated_v2: pd.DataFrame,
    *,
    store: CampaignObjectStore,
    key: str,
) -> str
    serialize parquet bytes
    store.put_new(key, body)
    return sha256
```

If any promotion id is missing from the curated frame, or is not medium, raise `ValueError`. If `select_promotions` sees fewer than 3000 scored rows, raise `ValueError`.

`write_curated_v2` uses `put_new`. If the v2 key exists, the command fails and does not replace it. Operators who need a rewrite delete the v2 object by hand first. The command has no path that writes the original `mirrorview.parquet` key.

`--write-v2` stdout includes:

```text
promotions=3000
v2_rows=43061
v2_sha256=<hex>
original_sha256=1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f
```

`RESULTS.md` records source and v2 URIs, both SHA-256 values, promotion count, the rank rule, and a `political_stance` by `llm_toxicity_tier` table for the v2 file. Original medium 20727 and high 913 become medium 17727 and high 3913 in the v2 file. The left and right split of the 3000 is measured after ranking, not fixed in advance.

After upload, download the v2 object and hash it. The hash must match the uploaded bytes. Download the original again and confirm its hash is still `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f`.

## Test design

No S3 and no Perspective.

```text
given scores with probs 0.9, 0.9, 0.1 and ids b, a, c
and count=2
when select_promotions
then [a, b]
because 0.9 ties break by source_record_id ascending

given a 4-row curated copy with two medium rows
and promotion ids of those two medium rows
when apply_promotions
then those two llm_toxicity_tier values are high
and every other cell equals the input
and row order is unchanged

given a promotion id whose current tier is low
when apply_promotions
then ValueError

given write_curated_v2 and a fake store whose put_new records the key
when write_curated_v2
then put_new is called with the v2 key
and replace is not called
and the original key is never used

given a fake store whose put_new raises FileExistsError
when write_curated_v2
then the error propagates
```

## Implementation notes (implement-from-spec)

Full auto. One Git commit per phase that changes the repo.

1. Scaffold `promote_v2.py`.
2. Lock signatures.
3. Add failing tests for tie-break, copy-only mutation, and `put_new`.
4. Phase 5:
   1. `select_promotions`
   2. `apply_promotions`
   3. `write_curated_v2` and `--write-v2`
   4. Live upload, `RESULTS.md`, README finish, changelog line
5. Phase 6. Pytest, then live `--write-v2`. Confirm original hash unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/experiments/test_reddit_curated_perspective_v2.py -q
```

Expected: exit 0 for Steps 1 through 3 tests.

Live write:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
```

Expected: exit 0, `promotions=3000`, `v2_rows=43061`, a new untagged `mirrorview_v2.parquet`, and the original object hash unchanged.

## Must fail / not happen

- `replace` or `put_new` on the original `mirrorview.parquet` key.
- Changing `metadata.json`.
- Promoting a comment that is not medium in the original file.
- Ranking with Perspective `toxicity_tier` instead of `toxicity_prob`.
- 2000 promotions, or 3000 per stance.
- Edits to `FEATURE_REGISTRY` or `mirrorview.yaml`.
