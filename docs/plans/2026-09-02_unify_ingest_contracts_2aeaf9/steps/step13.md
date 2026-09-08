# Step 13: Add a canonical source record id through feature and curate joins

## Goal

Feature CSVs today write a Bluesky-shaped `uri` id column for every platform, while preprocessed records keep native ids (`uri`, `tweet_id`, `comment_fullname`). Curation already special-cases non-Bluesky joins in `curate/runner.py`. This PR adds a shared `source_record_id` at preprocess, writes that name in feature files, and joins preprocessed native ids to feature `source_record_id` without renaming raw or curated native columns.

## Caller / unit of work

**Main callers:** `preprocess_records` in `data_platform/preprocessing/runner.py`; `generate_features` / engines in `data_platform/generate_features/`; `run_curation` → `build_wide_table` in `data_platform/curate/`.

**Slice:** preprocess adds `source_record_id` → feature labeling writes `source_record_id` in CSVs → curation joins native `records_id_column` to feature `source_record_id`.

**Out of scope:** Renaming raw Bluesky `uri`, Twitter `tweet_id`, Reddit `comment_fullname` / `reddit_fullname`. Stimuli sampling (`sample_data_to_mirror.py`) — it reads curated native id columns (`uri`, `tweet_id`, `post_reddit_id`), not feature file column names. Ingest sync. Step 11 text-column work.

## Decision (locked)

- Module constant `SOURCE_RECORD_ID_COLUMN = "source_record_id"` in `data_platform/utils/platform_specific_columns.py`.
- Do **not** rename platform-native id columns on raw rows or curated exports.
- Preprocess: after `add_canonical_text_column`, copy `spec.columns.records_id_column` into `source_record_id` (string). Native id column stays on the frame.
- `PlatformSpecificColumns.feature_file_id_column` becomes `"source_record_id"` for Bluesky, Twitter, and Reddit (replace today’s `"uri"` default on all three constants).
- Feature pydantic output models (`IsPoliticalModel`, `IsToxicTieredModel`, and the other five `*Model` classes under `generate_features/*/generate_feature.py`): rename field `uri` → `source_record_id`. Keep `generate_feature(uri: str, text: str)` parameter name `uri` (seven modules + `__main__` samples); construct models with `source_record_id=uri`. LangChain engine row assembly must use `source_record_id`, not `"uri"`.
- **`LabelTask.uri` → `LabelTask.record_id` (locked).** Blast is confined to `generate_features/` engines, orchestrator, and feature tests (~10 files). Do **not** rename `generate_feature(uri, …)` signatures in this PR.
- Curation: always pass both `id_column=spec.columns.records_id_column` and `feature_file_id_column=spec.columns.feature_file_id_column` into `ConsolidateConfig`. Remove the `if spec.columns.records_id_column != "uri"` guard in `curate/runner.py` — Bluesky now also needs explicit kwargs because feature files no longer use `uri`.
- `ConsolidateConfig` join contract unchanged: cast feature `source_record_id` to varchar and alias as preprocessed `id_column` for `USING` joins (`consolidate.py` `_feature_cte_sql`).
- Preprocessed storage models: add `source_record_id: str` to `PreprocessedRedditCommentModel`; add `PreprocessedBlueskyPostModel` and `PreprocessedTwitterPostModel` (sync fields + `source_record_id`; Reddit model keeps `text`). Wire `BlueskyStorageManager` and `TwitterStorageManager` to use preprocessed models when `stage == PREPROCESSED` (mirror `RedditStorageManager` today). Update feature platform specs’ `model_cls` to the preprocessed models so `load_preprocessed_records` validates the new column.
- `FeatureLabelQuery.feature_file_id_column` default becomes `"source_record_id"`.
- Independently shippable one PR. Existing on-disk feature CSVs with `uri` are out of scope — operators re-run feature generation or accept empty joins until relabeled.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 13 |
| `data_platform/utils/platform_specific_columns.py` | `records_id_column`, `feature_file_id_column` today |
| `data_platform/preprocessing/runner.py` | `preprocess_records` pipeline, `save_preprocessed` |
| `data_platform/models/sync.py` | `PreprocessedRedditCommentModel`; raw sync models |
| `data_platform/utils/storage.py` | `write_records` validation; Reddit preprocessed model switch |
| `data_platform/generate_features/models.py` | `LabelTask` |
| `data_platform/generate_features/generate_features.py` | `tasks_from_dataframe`, `id_column` wiring |
| `data_platform/generate_features/platform_cli.py` | `FeatureLabelQuery` construction |
| `data_platform/generate_features/engines/base.py` | `filter_seen_tasks`, deadletter `uris` list |
| `data_platform/generate_features/engines/langchain_engine.py` | hardcoded `"uri"` row key |
| `data_platform/generate_features/engines/thread_pool_engine.py` | `task.uri` → `generate_feature` |
| `data_platform/generate_features/*/generate_feature.py` | seven `*Model` classes with `uri: str` |
| `data_platform/generate_features/registry.py` | feature → model mapping |
| `data_platform/curate/consolidate.py` | `ConsolidateConfig`, `_feature_cte_sql` join |
| `data_platform/curate/runner.py` | `records_id_column != "uri"` special case |
| `data_platform/utils/feature_labels.py` | `feature_file_id_column` default |
| `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | confirm stimuli uses curated native ids only |
| `tests/data_platform/preprocessing/` | preprocess output columns |
| `tests/data_platform/generate_features/` | feature CSV id column, `LabelTask`, engines |
| `tests/data_platform/curate/` | consolidate join fixtures |
| `tests/data_platform/conftest.py` | `make_political_feature_rows`, `write_feature_csv` |
| `tests/data_platform/utils/test_platform_specific_columns.py` | column constants |

## Files allowed to change

- `data_platform/utils/platform_specific_columns.py`
- `data_platform/models/sync.py`
- `data_platform/utils/storage.py` (preprocessed model selection for Bluesky/Twitter)
- `data_platform/preprocessing/runner.py` (`add_source_record_id_column`, call site in `preprocess_records`)
- `data_platform/utils/feature_labels.py`
- `data_platform/generate_features/models.py`
- `data_platform/generate_features/generate_features.py`
- `data_platform/generate_features/platform_cli.py`
- `data_platform/generate_features/engines/base.py`
- `data_platform/generate_features/engines/langchain_engine.py`
- `data_platform/generate_features/engines/thread_pool_engine.py`
- `data_platform/generate_features/is_news_or_opinion/generate_feature.py`
- `data_platform/generate_features/is_political/generate_feature.py`
- `data_platform/generate_features/is_likely_spam/generate_feature.py`
- `data_platform/generate_features/is_self_contained/generate_feature.py`
- `data_platform/generate_features/is_structurally_complete/generate_feature.py`
- `data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `data_platform/generate_features/political_stance/generate_feature.py`
- `data_platform/generate_features/generate_bluesky_features.py` (preprocessed `model_cls`)
- `data_platform/generate_features/generate_twitter_features.py` (preprocessed `model_cls`)
- `data_platform/curate/runner.py`
- `tests/data_platform/preprocessing/test_add_canonical_text_column.py` or new `test_add_source_record_id_column.py`
- `tests/data_platform/preprocessing/test_preprocess_bluesky.py`
- `tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `tests/data_platform/utils/test_platform_specific_columns.py`
- `tests/data_platform/generate_features/test_engine_skip.py`
- `tests/data_platform/generate_features/test_langchain_engine.py`
- `tests/data_platform/generate_features/test_thread_pool_engine.py`
- `tests/data_platform/generate_features/test_is_likely_spam.py`
- `tests/data_platform/generate_features/test_generate_bluesky_features.py` (if present)
- `tests/data_platform/generate_features/test_generate_twitter_features.py`
- `tests/data_platform/generate_features/test_generate_reddit_features.py`
- `tests/data_platform/curate/test_consolidate.py`
- `tests/data_platform/curate/test_curate_bluesky.py` (if present)
- `tests/data_platform/curate/test_curate_twitter.py`
- `tests/data_platform/curate/test_curate_reddit.py`
- `tests/data_platform/conftest.py` (`make_political_feature_rows`, feature fixtures)
- `tests/data_platform/test_models_exports.py` (if preprocessed models are exported)
- `docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` (`feature_file_id_column` table row only)
- `CHANGELOG.md`

## Files forbidden to change

- `data_platform/ingestion/**`
- `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` (no feature `uri` join; native curated columns unchanged)
- Raw sync pydantic field names (`uri`, `tweet_id`, `comment_fullname`, `reddit_fullname`)
- Curated export column selection beyond what `posts.*` already carries (do not drop native ids or add stimuli-only renames)
- `data_platform/curate/consolidate.py` join SQL shape (only test/fixture column names unless a bug is found)

## Contracts

```text
SOURCE_RECORD_ID_COLUMN: str = "source_record_id"

add_source_record_id_column(df, records_id_column: str) -> pd.DataFrame
  out = df.copy()
  out[SOURCE_RECORD_ID_COLUMN] = out[records_id_column].astype(str)
  return out

PlatformSpecificColumns (all platforms):
  feature_file_id_column = SOURCE_RECORD_ID_COLUMN
  records_id_column unchanged (uri | tweet_id | comment_fullname)

LabelTask:
  record_id: str   # was uri; holds the platform record id from the input table
  text: str

Feature CSV row keys (all seven features):
  source_record_id, label_timestamp, <feature fields…>
  No uri column in new writes.

ConsolidateConfig (curate/runner.py always sets):
  id_column = spec.columns.records_id_column
  feature_file_id_column = spec.columns.feature_file_id_column  # source_record_id

Join (unchanged SQL semantics in consolidate.py):
  posts.{records_id_column} = CAST(feat.{source_record_id} AS VARCHAR)
  Wide table retains posts.* (native ids + source_record_id + text + features).
```

Preprocess call order in `preprocess_records`:

```text
records = add_canonical_text_column(records, spec)
records = add_source_record_id_column(records, spec.columns.records_id_column)
preprocessed = apply_text_transform(records, spec)
preprocessed = filter_records(preprocessed, spec)
```

## Tests (write first)

`TestAddSourceRecordIdColumn` in preprocessing tests:

- given a frame with `comment_fullname`, when `add_source_record_id_column` runs, then `source_record_id` equals string copy and `comment_fullname` is unchanged.
- given Bluesky `uri` column, then `source_record_id` matches `uri` and `uri` column remains.

`TestPlatformSpecificColumns`:

- all three platform constants set `feature_file_id_column == "source_record_id"`.

`TestLabelTaskRecordId` / update `test_engine_skip.py`:

- `filter_seen_tasks` matches on `task.record_id` against feature file `source_record_id` column.

`test_langchain_engine.py` / `test_thread_pool_engine.py`:

- written CSV rows include `source_record_id`, not `uri`.

`test_consolidate.py`:

- default Bluesky fixture feature rows use `source_record_id` key; Reddit mapping test uses `feature_file_id_column="source_record_id"` with `id_column="comment_fullname"`.

`test_curate_twitter.py` / `test_curate_reddit.py`:

- feature fixture dicts keyed by `TWITTER_COLUMNS.feature_file_id_column` / `REDDIT_COLUMNS.feature_file_id_column` (now `source_record_id`).

Preprocess integration tests (`test_preprocess_*`):

- saved preprocessed CSV includes `source_record_id` equal to native id.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per new function.

## Must pass

```bash
PYTHONPATH=. uv run pytest \
  tests/data_platform/preprocessing \
  tests/data_platform/generate_features \
  tests/data_platform/curate \
  tests/data_platform/utils/test_platform_specific_columns.py \
  tests/data_platform/test_models_exports.py \
  -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0. No new failures.

## Must not happen

- Renaming raw `uri`, `tweet_id`, `comment_fullname`, or `reddit_fullname`.
- Changing `sample_data_to_mirror.py` or stimuli native id columns on curated CSV (`uri`, `tweet_id`, `post_reddit_id`).
- Renaming `generate_feature(uri, text)` function signatures across the seven feature modules.
- Leaving feature CSVs writing `uri` while constants say `source_record_id`.
- Bluesky curation regressing because `ConsolidateConfig` still relies on default `feature_file_id_column="uri"`.
