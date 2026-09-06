# Wide consolidation and MirrorView curation report

## Approval

Phase B labeling finished on all seven features after explicit chat approval on 2026-09-06 ("Approved, run Phase B"). This step did not call OpenAI. Inputs are the seven `final.parquet` objects from issues #188 through #194.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Join key | `source_record_id` |
| Sort | `source_record_id ASC` |
| Wide columns | 19 |

## Inputs

Preprocessed posts SHA-256: `3d267201de22378e2d5e1a2c9eb4eae4ab3bc174aca5a134233caa54df3578fe`

| Feature | Manifest SHA-256 | `final.parquet` SHA-256 | Rows |
|---------|------------------|-------------------------|------|
| `is_news_or_opinion` | `e748731099742f44f6ef8fee4ac765d53c0334909059b2de481dd03193985373` | `3f6df9aa274200699b9f9fc629b4f4ef30842904f1513a845744fa6815810578` | 200000 |
| `is_political` | `1763c3ddbff26760ba6013d050386868b99c98f438f55ea34054a8fecf5318bb` | `16b075af1d0cfb8462af7725a6070d16d53463fa3027b907449e0e4a11f0efd2` | 200000 |
| `is_likely_spam` | `74e5217ba7cc865fb3978152371c92cf678ce4b0129928d99345dc9410ad719c` | `63744f16ff1c4000d26fa56aa6f426a447b27a1bf7a8e877c882937e17d308b9` | 200000 |
| `is_self_contained` | `0fa904f6bf98520a1dffb55ac07345d78c2fe04faa3bb484d3eb82187fe11362` | `197730b899d72bd4d19779491f7559a2a44e3156cfcec0befeb752c332df7e80` | 200000 |
| `is_structurally_complete` | `e4ac85948718ddb32d135620a50452e14f85ee14d31b37a6c1b0d828bb440b00` | `d8dfd9f51e577c7d2e505fe77e75e3be98b4cc4c7e2dfc333c7f818cd199049c` | 200000 |
| `political_stance` | `d504479532a619f06b7ea42af49536a88e5035aa266f61d9b4de8914524370df` | `302a8be18289b79213763f206a5c109d257a4f65f93ef4b364cbc73b3bddf017` | 200000 |
| `llm_toxicity_tiered` | `ab1448d35eaa5ff47a24aea2d3eac8316999acbf2d4f0d6ccfe5a43c27f75916` | `e959114311fbe71b998f4f7fb321627a4c6d85bcfbf469a5b5c6f1446f9ac1b0` | 200000 |

Each feature `final.parquet` SHA-256 matched its provenance manifest before the join.

## Wide outputs

| Object | URI | SHA-256 |
|--------|-----|---------|
| Wide parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet` | `5d8f2ff41acf25387df49804373bd6b88049af752654544d335dd3d47ab9fc3d` |
| Wide manifest | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/manifest.json` | `ed87f2c09ea18579abac8538a039dbc1f0502a7abafcbdd4520fd24165864f74` |

Wide objects are untagged. The join is an inner join on `CAST(source_record_id AS VARCHAR)`. Duplicate feature rows keep the latest `label_timestamp`. Perspective columns are absent.

Column order:

`uri`, `record_id`, `url`, `author_handle`, `text`, `created_at`, `like_count`, `repost_count`, `reply_count`, `quote_count`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Validation

All checks passed on 2026-09-06 after download to `/tmp/phaseb/wide/`.

| Check | Result |
|-------|--------|
| Nineteen columns in contract order | PASS |
| `wide_rows=200000` and 200000 distinct `source_record_id` | PASS |
| File order matches `source_record_id ASC` | PASS |
| Nulls on seven label columns | 0 |
| Missing preprocessed posts after join | 0 |
| Forbidden columns (`toxicity_prob`, `toxicity_tier`, `label_timestamp`, `run_id`, `is_toxic_tiered`) | absent |
| Wide parquet SHA-256 matches manifest | PASS |
| All seven feature manifests linked by SHA-256 | PASS |

## MirrorView curated dataset

Rules file: `data_platform/curate/configs/bluesky/mirrorview.yaml` (SHA-256 `62a0ee4f4b8528b7e75382b0ddab3f21857b9f23101f5ebdc5d0926c99aa53ff`). Filters are AND, in YAML order. No extra toxicity filter.

| Filter | Records before | Records passing |
|--------|----------------|-----------------|
| `news_or_opinion_category` eq `opinion` | 200000 | 77728 |
| `is_political` eq true | 77728 | 38596 |
| `is_likely_spam` eq false | 38596 | 38577 |
| `political_stance` in `left`, `right` | 38577 | 14339 |
| `is_self_contained` eq true | 14339 | 9990 |
| `is_structurally_complete` eq true | 9990 | 9756 |

**Curated row count: 9756**

| Object | URI | SHA-256 |
|--------|-----|---------|
| Curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/curated/mirrorview.parquet` | `35e3f05111a16c27b95538894cda18db6d7295c8aad6be4fb7cb83ecafb1b3bc` |
| Curated metadata | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/curated/metadata.json` | `b8c3c57ea75673026dcf120b07375f64b40b7bb94261f60df6db91624aa1e3d1` |

### Row count by political stance × LLM toxicity tier

| political_stance | low | medium | high | total |
|------------------|-----|--------|------|-------|
| left | 3563 | 4179 | 585 | 8327 |
| right | 529 | 755 | 145 | 1429 |
| total | 4092 | 4934 | 730 | 9756 |

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. python data_platform/curate/consolidate_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet
```

Stdout included seven accepted manifest digests, `wide_rows=200000`, `wide_columns=19`, `sort_key=source_record_id ASC`, `curated_rows=9756`, and the stance × toxicity table above.
