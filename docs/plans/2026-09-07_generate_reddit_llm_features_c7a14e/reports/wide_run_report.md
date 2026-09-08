# Wide consolidation and MirrorView curation report

## Approval

The epic manager started this step after all seven S3 `final.parquet` objects were verified at 400000 rows and 0 failed, with Phase B reports committed on stack PRs #242 through #248. The owner said not to merge those PRs first. This step did not call OpenAI or Bedrock. Inputs are the seven `final.parquet` objects from issues #222 through #228.

Feature reports (read-only here; hashes below are S3 bytes, not ETag):

- [`is_news_or_opinion_run_report.md`](is_news_or_opinion_run_report.md) (issue #222, PR #242)
- [`is_political_run_report.md`](is_political_run_report.md) (issue #223, PR #243)
- [`is_likely_spam_run_report.md`](is_likely_spam_run_report.md) (issue #224, PR #244)
- [`is_self_contained_run_report.md`](is_self_contained_run_report.md) (issue #225, PR #245)
- [`is_structurally_complete_run_report.md`](is_structurally_complete_run_report.md) (issue #226, PR #246)
- [`political_stance_run_report.md`](political_stance_run_report.md) (issue #227, PR #247)
- [`llm_toxicity_tiered_run_report.md`](llm_toxicity_tiered_run_report.md) (issue #228, PR #248)

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Join key | `source_record_id` |
| Sort | `source_record_id ASC` |
| Wide columns | 16 |

## Inputs

Preprocessed comments SHA-256: `c81ff327c2bc5a612b0f38b9d799e618f9d03ea3d3c4aff2d0f2a5f52a06ea31`

| Feature | Manifest SHA-256 | `final.parquet` SHA-256 | Rows |
|---------|------------------|-------------------------|------|
| `is_news_or_opinion` | `bd52ead3736c3c9a6d4a3bb9e0617cc6dcfc200f58513366ed919bcfb25319ac` | `f75e63e66cf95afdc5267a04fa8e2b5b45326e7cba9f12873bb86e296a07d390` | 400000 |
| `is_political` | `146d8c1e83e414d99e2f6b16e0a0dc6e1be7fbeb90e565f02b956bd9a2849996` | `041802dc9197b0f28bfa91e9f17d0bb8da9f5b02317dd5b78a87b48dc757dece` | 400000 |
| `is_likely_spam` | `acac3b81c2fa835cc002c3ee76ceaa358c15be9c2353626d054d992967442b9a` | `a2b835f2a2a350a427e9081a6e6d0d43f64b47a252466bd8ac7169de015f2484` | 400000 |
| `is_self_contained` | `eab5a83e6775d33511f3ed6870f11260a091b9e184a83885249287cf8ff6212e` | `fcddb19da531d013150716341657ba7115844913b63850afe1fd80a01a5d77e5` | 400000 |
| `is_structurally_complete` | `da58b5082bb6fb07b56644c2b43703d339839fda282041888d7092282f6e2d4e` | `161d85dfb7262bd67b4ae8c60abce9b96d290c52f74e62e5f261cf2289216140` | 400000 |
| `political_stance` | `4e1f21b2f8e48a529c89f7922f02fe5a32333ca26e4ef423c1d09978a66fb7f9` | `a034021e56646cabb69dc2ba8baf81d1042581cd710edbdd576702b26e801d24` | 400000 |
| `llm_toxicity_tiered` | `8c555b34fae3621770b379ad0a3174ed1fdf7601e2190ff922c6e51cc2606d66` | `bb0c0dabfc3b759b4c4403c1f2c68e04a2e94c41369de11e971d8d9177ce300c` | 400000 |

Each feature `final.parquet` SHA-256 matched its provenance manifest before the join.

## Wide outputs

| Object | URI | SHA-256 |
|--------|-----|---------|
| Wide parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/wide/features.parquet` | `e83dc0329cf1189eec1c27c6063c64260f191ae40ce24fee3efcd9be2f73df47` |
| Wide manifest | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/wide/manifest.json` | `3a01829edf5a4de789968ad10e89f2b9bd1f394aa5951b98443b293591f24087` |

Wide objects are untagged. The join is an inner join on `CAST(source_record_id AS VARCHAR)`. Duplicate feature rows keep the latest `label_timestamp`. Perspective columns are absent. Bluesky post columns (`uri`, `url`, engagement counts) are absent.

Column order:

`comment_fullname`, `record_id`, `author`, `body`, `created_at`, `sync_timestamp`, `text`, `author_handle`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Validation

All checks passed on 2026-09-07 after the consolidate CLI uploaded the wide objects.

| Check | Result |
|-------|--------|
| Sixteen columns in contract order | PASS |
| `wide_rows=400000` and 400000 distinct `source_record_id` | PASS |
| File order matches `source_record_id ASC` | PASS (`t1_mpxmfe6` … `t1_n0o71e2`) |
| Nulls on seven label columns | 0 |
| Missing preprocessed comments after join | 0 |
| Forbidden columns (`toxicity_prob`, `toxicity_tier`, `label_timestamp`, `run_id`, `is_toxic_tiered`) | absent |
| Wide parquet SHA-256 matches manifest | PASS |
| All seven feature manifests linked by SHA-256 | PASS |
| Wide parquet and manifest untagged | PASS |

## MirrorView curated dataset

The export uses the same dataset-stage layout as local `curate_reddit.py` runs: `curated/<timestamp>/mirrorview.parquet` plus `metadata.json` under `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/`. It is not stored under the campaign `wide/` prefix. Writes went through `RedditStorageManager("curated", dataset_id)`.

Rules file: `data_platform/curate/configs/reddit/mirrorview.yaml` (SHA-256 `62a0ee4f4b8528b7e75382b0ddab3f21857b9f23101f5ebdc5d0926c99aa53ff`). Filters are AND, in YAML order. YAML was not edited.

| Filter | Records before | Records passing |
|--------|----------------|-----------------|
| `news_or_opinion_category` eq `opinion` | 400000 | 299283 |
| `is_political` eq true | 299283 | 248326 |
| `is_likely_spam` eq false | 248326 | 248184 |
| `political_stance` in `left`, `right` | 248184 | 100764 |
| `is_self_contained` eq true | 100764 | 45385 |
| `is_structurally_complete` eq true | 45385 | 43061 |

**Curated row count: 43061**

| Object | URI | SHA-256 |
|--------|-----|---------|
| Curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview.parquet` | `1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f` |
| Curated metadata | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/metadata.json` | `740b9e5cb7cc9253a60bb959265fd07cd72afb41b466086130b861c01dfd9886` |

### Row count by political stance × LLM toxicity tier

| political_stance | low | medium | high | total |
|------------------|-----|--------|------|-------|
| left | 13423 | 15047 | 641 | 29111 |
| right | 7998 | 5680 | 272 | 13950 |
| total | 21421 | 20727 | 913 | 43061 |

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_reddit_llm_campaign.py \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/wide/features.parquet
```

Stdout included seven accepted manifest digests, `wide_rows=400000`, `wide_columns=16`, `sort_key=source_record_id ASC`, `curated_rows=43061`, and the stance × toxicity table above.
