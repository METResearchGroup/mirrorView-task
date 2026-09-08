# Step 1: Add the combine script

## Scope

- **Caller:** `experiments/combine_data_into_stimulus_set_2026_09_08/run.py` `main`
- **Task:** Download four pinned curated parquet files from S3, check each file's SHA-256 and row count, normalize to a shared column set, concatenate, write local `dataset.parquet`, upload that file to S3 with `put_new`, print two crosstab tables, and write `RESULTS.md`.
- **Out of scope:** pytest, relabeling, curation YAML edits, `sample_data_to_mirror.py`, generating mirrors, changing product curate scripts, overwriting the four source objects.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md` | Bluesky curated URI, hash, 9756 rows, stance by toxicity |
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md` | Twitter collection 1 curated URI, hash, 1457 rows |
| `/workspace/docs/plans/2026-09-08_join_twitter_llm_curate_19e01b/reports/wide_run_report.md` | Twitter collection 2 curated URI, hash, 1299 rows |
| `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/wide_run_report.md` | Original Reddit curated URI and 43061 rows |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/RESULTS.md` | Reddit second file URI, hash, v2 stance by toxicity |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/load_curated.py` | Download, hash check, `CampaignObjectStore.get` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore`, `parse_s3_uri`, `put_new` |
| `/workspace/data_platform/utils/object_store.py` | `sha256_hex`, `DEFAULT_S3_BUCKET`, `DEFAULT_S3_REGION` |
| `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py` | Stance rows `left`/`right`, toxicity columns `low`/`medium`/`high` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/run.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/sources.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/load.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/normalize.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/crosstab.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/write.py` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/README.md` (new)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore local parquet and cache under this experiment folder only)

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/consolidate_reddit_llm_campaign.py`
- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py`
- `/workspace/data_platform/curate/configs/**`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/**`
- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/**`
- `/workspace/tests/**`
- The four source S3 objects listed below
- `/workspace/CHANGELOG.md` until Step 2 has a live S3 object and RESULTS.md

## Pinned sources

Use these four objects. Reddit uses the second file `mirrorview_v2.parquet`, not the original `mirrorview.parquet`.

| Platform | Dataset id | Curated run | Object | SHA-256 | Rows |
|----------|------------|-------------|--------|---------|-----:|
| bluesky | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` | `2026_09_06-23:25:06` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/curated/2026_09_06-23:25:06/mirrorview.parquet` | `35e3f05111a16c27b95538894cda18db6d7295c8aad6be4fb7cb83ecafb1b3bc` | 9756 |
| twitter | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` | `2026_09_07-06:58:09` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/curated/2026_09_07-06:58:09/mirrorview.parquet` | `7639e54554869371fdb6397a1c2a497b32711679290322b999fb68ee173f39c9` | 1457 |
| twitter | `twitter_5901767a-e609-46fc-9a17-742516b548f2` | `2026_09_08-05:34:19` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/curated/2026_09_08-05:34:19/mirrorview.parquet` | `c2178c27165c26dd960bd470e3ee98791e7c98638a346eca0f0fafa1c065c8e2` | 1299 |
| reddit | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` | `2026_09_07-21:47:32` | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/mirrorview_v2.parquet` | `e1d9b1494fd2ef030dc8fdc1f71980b55d972e4a01da23923fa6f61a693a3936` | 43061 |

Combined expected row count: 55573.

## Shared column contract

The combined parquet has these columns in this order:

1. `integration`
2. `source_dataset_id`
3. `source_curated_run`
4. `record_id`
5. `source_record_id`
6. `platform_id`
7. `author_handle`
8. `text`
9. `created_at`
10. `sync_timestamp`
11. `news_or_opinion_category`
12. `is_political`
13. `is_likely_spam`
14. `is_self_contained`
15. `is_structurally_complete`
16. `political_stance`
17. `llm_toxicity_tier`

`platform_id` comes from `uri` on Bluesky, `tweet_id` on Twitter, and `comment_fullname` on Reddit.

`text` is the existing standardized `text` column on every source. Do not use Reddit `body`.

`integration` values are `bluesky`, `reddit`, and `twitter`.

Sort the combined table by `integration` ascending, then `source_dataset_id` ascending, then `source_record_id` ascending. Do not drop rows. Do not dedupe across the two Twitter collections. If a tweet id appears in both Twitter files, keep both rows.

A missing required column, a hash mismatch, or a wrong source row count raises `ValueError`. A missing source object raises `FileNotFoundError`.

## Outputs

| Output | Path |
|--------|------|
| Local parquet | `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` |
| S3 key | `experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` |
| Report | `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/RESULTS.md` |
| Cache | `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/cache/` (gitignored) |

Upload with `CampaignObjectStore.put_new`. The write fails if the S3 key already exists. Record SHA-256 of the parquet bytes as object metadata the same way `put_new` already does.

Gitignore `cache/` and `dataset.parquet` under this experiment folder. Do not commit the parquet.

## Crosstab contract

Stance rows are `left` and `right`. Toxicity columns are `low`, `medium`, and `high`. Missing cells count as 0.

Table 1 is overall `political_stance` by `llm_toxicity_tier` across all 55573 rows, with row totals and a total row.

Table 2 is the same counts split by `integration`. One markdown table with columns `integration`, `political_stance`, `low`, `medium`, `high`, `total`. Platform order is `bluesky`, `reddit`, `twitter`. The two Twitter collections are one `twitter` group. Include a total row per platform and a grand total row.

Stdout prints both tables as JSON, plus `combined_rows=55573` and the local and S3 URIs and SHA-256.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
```

Expected stdout includes `combined_rows=55573`, `local_path=`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet`, `dataset_sha256=`, and the two JSON tables.

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then live checks below, written in the `run.py` module docstring.

### Modules

Keep functions under 20 lines. Use a frozen dataclass for each pinned source. Do not pass unstructured dictionaries for source identity.

`sources.py` holds `CuratedSource` and the four pinned records.

`load.py` downloads one source through `CampaignObjectStore.get`, checks SHA-256 with `sha256_hex`, checks row count, and may cache bytes under `cache/`.

`normalize.py` maps one source frame onto the 17 shared columns.

`crosstab.py` builds the two count tables.

`write.py` writes local parquet bytes, uploads with `put_new`, and writes `RESULTS.md`.

`run.py` is the caller: load all four, normalize, concatenate, sort, write, print.

Reuse `CampaignObjectStore`, `parse_s3_uri`, and `sha256_hex`. Do not copy a new S3 client.

### Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the four pinned curated objects exist at the hashes above
when PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
then combined_rows=55573
and local dataset.parquet exists
and S3 object experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet exists
and its SHA-256 matches the local file
and RESULTS.md contains the overall stance by toxicity table
and RESULTS.md contains the three-platform stance by toxicity table
and stdout prints both tables

given the S3 dataset.parquet key already exists
when the command is run again
then the process raises FileExistsError and does not change the four source objects
```

## Must pass

- Imports from `run.py` resolve.
- Combined row count is 55573 after a live run in Step 2.
- Combined columns match the 17-name contract in order.
- Reddit source is `mirrorview_v2.parquet`.
- Product curate files are unchanged.

## Must fail

- Hash mismatch on any source.
- Wrong source row count.
- Missing required column on a source.
- Second upload to the same S3 key.

## Implement-from-spec notes

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds the six modules with stub bodies and a thin `main` that calls load, normalize, concatenate, write, print.

Phase 3 locks `CuratedSource` and the public function signatures. Continue without a pause because this run is full auto.

Phase 4 writes the given/when/then block in the `run.py` docstring. Do not add files under `tests/`.

Phase 5 implements in this order, one commit per unit of work:

1. `CuratedSource` and `PINNED_SOURCES`
2. download and hash/row checks
3. normalize to 17 columns
4. concatenate and sort
5. crosstab builders
6. local parquet write
7. S3 `put_new`
8. RESULTS.md writer and `main`

Phase 6 is complete when the modules exist, imports resolve, and Step 2 can run the live command.
