# Wide consolidation and MirrorView curation report

## Approval

Phase B labeling finished on all seven features on pull request 264. This step did not call OpenAI. Inputs are the seven `final.parquet` objects for campaign `twitter_2026_09_08_014808_llm_features_v1`.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_5901767a-e609-46fc-9a17-742516b548f2` |
| Preprocessed run | `2026_09_08-01:48:08` |
| Preprocessed row count | 6408 |
| Preprocessed file | `posts.csv` |
| Campaign id | `twitter_2026_09_08_014808_llm_features_v1` |
| Join key | `source_record_id` |
| Sort | `source_record_id ASC` |
| Wide columns | 21 |

## Inputs

Preprocessed posts SHA-256: `0461a0dc7ac5ecf1c5699fa893013dc7165af482a5347067e413bf4315ffdbd2`

The SHA-256 matches `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/s3_preprocessed_inventory.json`.

| Feature | Manifest SHA-256 | `final.parquet` SHA-256 | Rows |
|---------|------------------|-------------------------|------|
| `is_news_or_opinion` | `abe6a45094ad51d26d843c3af651214f9713c482be4ed0976dfb370e3d424574` | `fc8ab8676868fe426f1f26be496776919c637aab1ea5a30042402ccaeabf2421` | 6408 |
| `is_political` | `6df5db12221cadc3bcb201081c14e0f1c65eb2f1c395075ab8031006fadffa93` | `f981f44ea8e9b42c3160d158a5de388b6fed0cbbfdb94a71d85ea340c56e8c53` | 6408 |
| `is_likely_spam` | `2d84188dfe96a5b60799bf39643268d9b6410d1383c5abeb6760bdac2cc51833` | `0ce265bfd54601609d4b32937ce9d925fcb38cc4ae3e5f1916b83940541ec493` | 6408 |
| `is_self_contained` | `7eb49dd608ffb883e813cb6806f9a243ca6ea46628f4c91d830c1e6a91783c7e` | `577c0da3d3412bb2cbc112844cc5485686c5a8cfdbc52e6aa0954bd100339872` | 6408 |
| `is_structurally_complete` | `a1243a14fc8860b9239aa1f041555f1c617535558837b6140105c6a00acec7dc` | `6ba54e2d34087bcd651671bbe4180f46765d0c41c2159bd429270eff427739cd` | 6408 |
| `political_stance` | `488360c09209720fc8ecb5d3b1180acd4c3d96f1a7f77757bcf5073e57c7d24c` | `d1566660247cd36c6fa4211952e28e91ce896db31c2d8a42ec04bfa6c7db2793` | 6408 |
| `llm_toxicity_tiered` | `d25a94cf238021570a6ab3c70c7a2715f338807b88c4314b53c3f9e0744106d0` | `1011fa84ab7303463d3bcefed04de705232d171f662d03961f88c71f8e3747c6` | 6408 |

Each feature `final.parquet` SHA-256 matched its parameter manifest before the join.

## Wide outputs

| Object | URI | SHA-256 |
|--------|-----|---------|
| Wide parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet` | `b566bcba6c3e5fd83c6e35d7cf169dac68cd85bc1d425f159dbc068bb61b1ffe` |
| Wide manifest | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/manifest.json` | `7dae14e96ac61860ef6a66a754407b9609d7a17007177bce906478fffc5115fb` |

Wide objects are untagged. The join is an inner join on `CAST(source_record_id AS VARCHAR)`. Duplicate feature rows keep the latest `label_timestamp`. The left table is csv `posts.csv`. `author_id` is absent.

Column order:

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Validation

All checks passed on 2026-09-08 after download to `/tmp/twitter_2026_09_08_wide.parquet`.

| Check | Result |
|-------|--------|
| Twenty-one columns in contract order | PASS |
| `wide_rows=6408` and 6408 distinct `source_record_id` | PASS |
| File order matches `source_record_id ASC` | PASS |
| Nulls on seven label columns | 0 |
| Missing preprocessed posts after join | 0 |
| Forbidden columns (`toxicity_prob`, `toxicity_tier`, `label_timestamp`, `run_id`, `is_toxic_tiered`, `author_id`) | absent |
| Wide parquet SHA-256 matches manifest | PASS |
| All seven feature manifests linked by SHA-256 | PASS |
| Preprocessed csv SHA-256 matches inventory | PASS |
| Expected row count from campaign YAML | 6408 |

## MirrorView curated dataset

The export uses the dataset-stage layout: `curated/<timestamp>/mirrorview.parquet` plus `metadata.json` under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/`. It is not stored under the campaign `wide/` prefix. `TwitterStorageManager("curated", dataset_id)` created the run directory and wrote `metadata.json`.

Rules file: `data_platform/curate/configs/twitter/mirrorview.yaml` (SHA-256 `62a0ee4f4b8528b7e75382b0ddab3f21857b9f23101f5ebdc5d0926c99aa53ff`). Filters are AND, in YAML order. No extra toxicity filter.

| Filter | Records before | Records passing |
|--------|----------------|-----------------|
| `news_or_opinion_category` eq `opinion` | 6408 | 3558 |
| `is_political` eq true | 3558 | 3067 |
| `is_likely_spam` eq false | 3067 | 3057 |
| `political_stance` in `left`, `right` | 3057 | 2108 |
| `is_self_contained` eq true | 2108 | 1326 |
| `is_structurally_complete` eq true | 1326 | 1299 |

Curated row count: 1299

| Object | URI | SHA-256 |
|--------|-----|---------|
| Curated parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/curated/2026_09_08-05:34:19/mirrorview.parquet` | `c2178c27165c26dd960bd470e3ee98791e7c98638a346eca0f0fafa1c065c8e2` |
| Curated metadata | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/curated/2026_09_08-05:34:19/metadata.json` | `73de52372d6615b16cd8dc6817aa79b16fdcb061a1990147bad45f82db8f8733` |

### Row count by political stance × LLM toxicity tier

Valid curated rows only. Stance rows are `left` and `right`. Toxicity columns are `low`, `medium`, and `high`.

| political_stance | low | medium | high | total |
|------------------|-----|--------|------|-------|
| left | 512 | 118 | 9 | 639 |
| right | 342 | 245 | 73 | 660 |
| total | 854 | 363 | 82 | 1299 |

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08 \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet
```

Stdout included seven accepted manifest digests, `wide_rows=6408`, `wide_columns=21`, `sort_key=source_record_id ASC`, `curated_rows=1299`, and the stance × toxicity table above.
