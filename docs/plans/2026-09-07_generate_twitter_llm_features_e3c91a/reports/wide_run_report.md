# Wide consolidation and MirrorView curation report

## Approval

Phase B labeling finished on all seven features on pull request 240. This step did not call OpenAI. Inputs are the seven `final.parquet` objects for campaign `twitter_2026_09_06_192847_llm_features_v1`.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | 6374 |
| Preprocessed file | `posts.csv` |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Join key | `source_record_id` |
| Sort | `source_record_id ASC` |
| Wide columns | 21 |

## Inputs

Preprocessed posts SHA-256: `7233223b21210d0937372d9d906abfd914962784402d6b167805952a7415fa4a`

The SHA-256 matches `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json`.

| Feature | Manifest SHA-256 | `final.parquet` SHA-256 | Rows |
|---------|------------------|-------------------------|------|
| `is_news_or_opinion` | `bcf3ea67da954b6053543db1371c1f4044bb8d81e46fe4cc01df1554967fb349` | `f999ad42141a10ba82194979f3cf3f5673655db7e50d4696bf8100a2fed5fbaa` | 6374 |
| `is_political` | `69308ac0de12090e6d51dfc4ebb96e1226113f9ba801fa13213344847b1d5284` | `58b6dc78a222fe98dff13084176011b90fb4e650fd6d9a669c3d880af84c77e4` | 6374 |
| `is_likely_spam` | `1e0d47675d2af41b4f57fb1c4d347f646ddf687c62f41eb2ca0eb28a464c77d2` | `a96dd1446e9204adcbd1716629fde077e95d3ff49e4f46182fb56368f739e689` | 6374 |
| `is_self_contained` | `b6ce3062da1202019d0f5d0df9c0f19ba897607c163e7ebc0cd4fd2626026b4d` | `69d922ef1933ea3c236d5ea2ddced5e72cc940cfab31346afc6ccb23477f7da5` | 6374 |
| `is_structurally_complete` | `4aec69422431046445e1f29603c5506141a523c34fad54cfa8f47f85d64d19b6` | `76a8a0c83ffff41eb5842cb3581d4014e629baa5afd4f4ae2e073fc928d1939c` | 6374 |
| `political_stance` | `4f5dd74b01394bcfc5a7890ba9da2a5095e157cd6dbd3367734539e4229533e2` | `de7a67c77ffe98ccf439dca6f6ededb347a4658303424b9955d9a0e7d63d9c2e` | 6374 |
| `llm_toxicity_tiered` | `bdf80f10b6e3a7c6b1ab234536f4cf74d991e1c52f846da05a3137968ffd4e94` | `2e8a8fbcb742e219929a92598e0d3b8f9be5957ac6c43c8598f2c4f2e4668ea8` | 6374 |

Each feature `final.parquet` SHA-256 matched its parameter manifest before the join.

## Wide outputs

| Object | URI | SHA-256 |
|--------|-----|---------|
| Wide parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet` | `e5aa2d5313e7f69ae9f22230f0478bba54533f16cf4f19e891bc96d7b5b7751f` |
| Wide manifest | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/manifest.json` | `92b083df880639e48ae8d66a977330b6dec08813ec1c1a1492ec6b4977659e9d` |

Wide objects are untagged. The join is an inner join on `CAST(source_record_id AS VARCHAR)`. Duplicate feature rows keep the latest `label_timestamp`. The left table is csv `posts.csv`. `author_id` is absent.

Column order:

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Validation

All checks passed on 2026-09-07 after download to `/tmp/twitter_wide.parquet`.

| Check | Result |
|-------|--------|
| Twenty-one columns in contract order | PASS |
| `wide_rows=6374` and 6374 distinct `source_record_id` | PASS |
| File order matches `source_record_id ASC` | PASS |
| Nulls on seven label columns | 0 |
| Missing preprocessed posts after join | 0 |
| Forbidden columns (`toxicity_prob`, `toxicity_tier`, `label_timestamp`, `run_id`, `is_toxic_tiered`, `author_id`) | absent |
| Wide parquet SHA-256 matches manifest | PASS |
| All seven feature manifests linked by SHA-256 | PASS |
| Preprocessed csv SHA-256 matches inventory | PASS |

## MirrorView curated dataset

The export uses the dataset-stage layout: `curated/<timestamp>/mirrorview.parquet` plus `metadata.json` under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/`. It is not stored under the campaign `wide/` prefix. `TwitterStorageManager("curated", dataset_id)` created the run directory and wrote `metadata.json`.

Rules file: `data_platform/curate/configs/twitter/mirrorview.yaml` (SHA-256 `62a0ee4f4b8528b7e75382b0ddab3f21857b9f23101f5ebdc5d0926c99aa53ff`). Filters are AND, in YAML order. No extra toxicity filter.

| Filter | Records before | Records passing |
|--------|----------------|-----------------|
| `news_or_opinion_category` eq `opinion` | 6374 | 3493 |
| `is_political` eq true | 3493 | 2984 |
| `is_likely_spam` eq false | 2984 | 2974 |
| `political_stance` in `left`, `right` | 2974 | 2103 |
| `is_self_contained` eq true | 2103 | 1484 |
| `is_structurally_complete` eq true | 1484 | 1457 |

Curated row count: 1457

| Object | URI | SHA-256 |
|--------|-----|---------|
| Curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/curated/2026_09_07-06:58:09/mirrorview.parquet` | `7639e54554869371fdb6397a1c2a497b32711679290322b999fb68ee173f39c9` |
| Curated metadata | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/curated/2026_09_07-06:58:09/metadata.json` | `ce8f5f1300065c117d00c8155d4649559bf449f487f5c83ba0079cf50d234b31` |

### Row count by political stance × LLM toxicity tier

Valid curated rows only. Stance rows are `left` and `right`. Toxicity columns are `low`, `medium`, and `high`.

| political_stance | low | medium | high | total |
|------------------|-----|--------|------|-------|
| left | 563 | 142 | 12 | 717 |
| right | 392 | 279 | 69 | 740 |
| total | 955 | 421 | 81 | 1457 |

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet
```

Stdout included seven accepted manifest digests, `wide_rows=6374`, `wide_columns=21`, `sort_key=source_record_id ASC`, `curated_rows=1457`, and the stance × toxicity table above.
