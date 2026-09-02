# Step 1: Add shared source record id through preprocess, feature files, and curate joins

## Goal

Give every preprocessed row a shared `source_record_id` equal to the platform's original record id, without renaming that original column. Write `source_record_id` in feature files. Join preprocessed original ids to that feature column for every platform.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/runner.py` `preprocess_records`, reached from `preprocess_bluesky.py`, `preprocess_reddit.py`, and `preprocess_twitter.py`. Downstream callers that must honor the new column name are `data_platform/generate_features/platform_cli.py` `build_feature_config` and `data_platform/curate/runner.py` `run_curation`.

**Task:** after `add_canonical_author_columns`, call `add_canonical_source_record_id`. Point `feature_file_id_column` at `source_record_id`. Always pass original record id and feature file id into consolidate. Validate extra preprocessed columns with the existing storage model swap, including a Bluesky preprocessed model.

**Out of scope:** Raw ingest writers and `Sync*` field lists. Length and language gates (GitHub issue 116). Stimuli sampling. Renaming `LabelTask.uri`. `CHANGELOG.md`. Sibling GitHub issues 103 to 114 and 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/runner.py` | `add_canonical_author_columns`, `preprocess_records`, `PreprocessPlatformSpec` |
| `/workspace/data_platform/utils/platform_specific_columns.py` | `feature_file_id_column` is `"uri"` on every platform |
| `/workspace/data_platform/curate/runner.py` | Special-cases `records_id_column != "uri"` |
| `/workspace/data_platform/curate/consolidate.py` | Joins original `id_column` to `feature_file_id_column` |
| `/workspace/data_platform/generate_features/engines/langchain_engine.py` | Writes `"uri": task.uri` into label rows |
| `/workspace/data_platform/generate_features/engines/thread_pool_engine.py` | Dumps feature models that currently name the id `uri` |
| `/workspace/data_platform/models/sync.py` | `PreprocessedRedditCommentModel`, `PreprocessedTwitterPostModel` |
| `/workspace/data_platform/utils/storage.py` | Reddit and Twitter already swap preprocessed models |
| `/workspace/tests/data_platform/preprocessing/test_add_canonical_author_columns.py` | Helper test shape |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function. Arrange, act, assert. |

## Files allowed to change

- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/utils/platform_specific_columns.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/generate_features/generate_bluesky_features.py` (`model_cls` only)
- `/workspace/data_platform/generate_features/engines/langchain_engine.py`
- `/workspace/data_platform/generate_features/is_likely_spam/generate_feature.py`
- `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py`
- `/workspace/data_platform/generate_features/is_political/generate_feature.py`
- `/workspace/data_platform/generate_features/is_self_contained/generate_feature.py`
- `/workspace/data_platform/generate_features/is_structurally_complete/generate_feature.py`
- `/workspace/data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `/workspace/data_platform/generate_features/political_stance/generate_feature.py`
- `/workspace/data_platform/curate/runner.py`
- `/workspace/data_platform/curate/consolidate.py` (docstring and default `feature_file_id_column` only)
- `/workspace/data_platform/utils/feature_labels.py` (default `feature_file_id_column` only)
- `/workspace/tests/data_platform/preprocessing/test_add_canonical_source_record_id.py` (new)
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py`
- `/workspace/tests/data_platform/utils/test_platform_specific_columns.py`
- `/workspace/tests/data_platform/generate_features/**` as needed for the new feature file id name and leftover `opik_enabled` kwargs
- `/workspace/tests/data_platform/curate/**` as needed so feature CSVs and joins use `source_record_id`
- `/workspace/tests/data_platform/utils/test_feature_labels.py`
- `/workspace/tests/data_platform/conftest.py` (`make_political_feature_rows` feature id key only)
- `/workspace/tests/data_platform/generate_features/test_is_likely_spam.py` and sibling feature schema tests that assert `.uri`

Plan package files under `/workspace/docs/plans/2026-09-02_shared_source_record_id_20d0de/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/**`
- Field lists on `SyncBlueskyPostModel`, `SyncRedditCommentModel`, `SyncRedditPostModel`, `SyncTwitterPostModel`
- `/workspace/data_platform/generate_features/models.py` `LabelTask.uri`
- Stimuli sampling under `/workspace/experiments/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add this constant in `/workspace/data_platform/utils/platform_specific_columns.py`:

```text
CANONICAL_SOURCE_RECORD_ID_COLUMN = "source_record_id"
```

`PlatformSpecificColumns.feature_file_id_column` default becomes `CANONICAL_SOURCE_RECORD_ID_COLUMN`. `BLUESKY_COLUMNS`, `REDDIT_COLUMNS`, and `TWITTER_COLUMNS` all use that name. Original `records_id_column` values stay `uri`, `comment_fullname`, and `tweet_id`.

Do not add a source-column field on `PreprocessPlatformSpec`. The copy source is always `spec.columns.records_id_column`.

```text
add_canonical_source_record_id(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame
```

- Returns a new frame. Does not mutate input.
- Require `spec.columns.records_id_column` on the frame.
- Set `source_record_id` to `str` of that original id.
- Keep the original id column.
- Raise `KeyError` when the original id column is missing.

`preprocess_records` order:

```text
records = add_canonical_text_column(records, spec)
records = add_canonical_author_columns(records, spec)
records = add_canonical_source_record_id(records, spec)
```

Then `apply_text_transform`, `filter_records`, and `save_preprocessed` stay as they are.

Models in `/workspace/data_platform/models/sync.py`:

```text
PreprocessedBlueskyPostModel(SyncBlueskyPostModel):
  source_record_id: str

PreprocessedRedditCommentModel(SyncRedditCommentModel):
  text: str
  author_handle: str
  source_record_id: str

PreprocessedTwitterPostModel(SyncTwitterPostModel):
  author_handle: str
  source_record_id: str
```

`BlueskyStorageManager` uses `PreprocessedBlueskyPostModel` when `stage == StorageStage.PREPROCESSED`, the same way Reddit and Twitter already swap models. `generate_bluesky_features.BLUESKY_SPEC.model_cls` becomes `PreprocessedBlueskyPostModel`.

Feature CSV models (`IsPoliticalModel` and the other stored feature row models) rename the stored id field from `uri` to `source_record_id`. `generate_feature` still takes the record id as its first string argument. LangChain engine rows use `source_record_id=task.uri`. Do not rename `LabelTask.uri`.

`FeatureLabelQuery.feature_file_id_column` and `ConsolidateConfig.feature_file_id_column` default to `source_record_id`.

`run_curation` always sets:

```text
consolidate_kwargs["id_column"] = spec.columns.records_id_column
consolidate_kwargs["feature_file_id_column"] = spec.columns.feature_file_id_column
```

Delete the `if spec.columns.records_id_column != "uri"` branch.

## Test design

Location: `/workspace/tests/data_platform/preprocessing/test_add_canonical_source_record_id.py`

Import `add_canonical_source_record_id` from `data_platform.preprocessing.runner`. One class: `TestAddCanonicalSourceRecordId`.

Use `mock_comment_row`, `mock_tweet_row`, and `make_post_row`.

```text
given a Reddit frame with comment_fullname="t1_keep"
when add_canonical_source_record_id(..., REDDIT_SPEC)
then source_record_id equals "t1_keep"
and comment_fullname is unchanged
and source_record_id is not on the input frame

given a Twitter frame with tweet_id="1000000000000000001"
when add_canonical_source_record_id(..., TWITTER_SPEC)
then source_record_id equals that tweet_id
and tweet_id is unchanged

given a Bluesky frame with uri="at://did:plc:example/app.bsky.feed.post/abc"
when add_canonical_source_record_id(..., BLUESKY_SPEC)
then source_record_id equals that uri
and uri is unchanged

given a Reddit frame missing comment_fullname
when add_canonical_source_record_id(..., REDDIT_SPEC)
then raise KeyError
```

Extend end-to-end preprocess tests. Reload through `StorageManager(StorageStage.PREPROCESSED, ...)`:

- Reddit `test_preprocess_records_writes_output`: saved row has `source_record_id == comment_fullname`.
- Twitter `test_preprocess_records_writes_output`: saved row has `source_record_id == tweet_id`.
- Bluesky `test_preprocessed_rows_include_text`: also assert `source_record_id` equals `uri`.

`test_platform_specific_columns.py` asserts `feature_file_id_column == CANONICAL_SOURCE_RECORD_ID_COLUMN` for Bluesky, Reddit, and Twitter.

Update feature-generation sample rows so they include `source_record_id` copied from the original id. Feature CSV fixtures and engine schema tests that currently write or assert `uri` as the stored feature id use `source_record_id` instead. Preprocessed native id columns in those tests stay as they are.

`test_build_wide_table_supports_reddit_id_column_mapping` joins `comment_fullname` to feature `source_record_id`. Bluesky consolidate tests join preprocessed `uri` to feature `source_record_id`.

If `tests/data_platform/generate_features/test_platform_cli.py` still passes unused `opik_enabled` kwargs, drop those kwargs so the issue's generate_features command can exit 0. Do not expand into other Opik cleanup.

## Implementation notes (implement-from-spec)

The author-handle helper already exists. Scaffold a stub source-record-id helper. Full auto. Do not wait for approval.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm callers, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `add_canonical_source_record_id` that raises `NotImplementedError`. Add `/workspace/tests/data_platform/preprocessing/test_add_canonical_source_record_id.py` with the import and an empty `TestAddCanonicalSourceRecordId` class. Do not call the helper from `preprocess_records` yet.
3. Phase 3 contracts. Add `CANONICAL_SOURCE_RECORD_ID_COLUMN`, the helper signature and docstring, `source_record_id` on the three preprocessed models, and `feature_file_id_column` still left as production `"uri"` until a later unit if changing it now would make unrelated tests fail before tests exist. Helper body still raises `NotImplementedError`. Full auto.
4. Phase 4 test design. Add the failing helper tests and the end-to-end assertions. Helper tests fail because of `NotImplementedError`.
5. Phase 5 units, in this order, one commit each:
   1. Implement `add_canonical_source_record_id`. Helper tests pass. End-to-end preprocess tests stay red until the caller is wired.
   2. Call `add_canonical_source_record_id` from `preprocess_records` after the author helper. Swap Bluesky, Reddit, and Twitter preprocessed storage and Bluesky feature `model_cls` so writes accept `source_record_id`. End-to-end preprocess tests pass.
   3. Set `feature_file_id_column` to `source_record_id` on the platform column constants and on the FeatureLabelQuery and ConsolidateConfig defaults. Update feature CSV fixtures and platform column tests.
   4. Rename stored feature model id fields and LangChain engine output to `source_record_id`. Engine and feature schema tests pass.
   5. Always pass both curate join kwargs. Drop the `records_id_column != "uri"` special case. Curate tests pass.
   6. Drop leftover `opik_enabled` kwargs in `test_platform_cli.py` if the issue's generate_features command still fails on those three tests.
6. Phase 6. Run the must-pass commands. Confirm ingest writers are unchanged. Confirm original id columns remain. Confirm `CHANGELOG.md` is unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing tests/data_platform/generate_features tests/data_platform/curate tests/data_platform/utils/test_platform_specific_columns.py tests/data_platform/test_models_exports.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0 with no new failures. Unused `opik_enabled` kwargs may be dropped if required for the first command to exit 0.

## Must fail / not happen

- Raw ingest writers renamed or duplicated (`tweet_id` rewritten to `source_record_id` at sync time).
- Original preprocessed id columns removed (`uri`, `comment_fullname`, `tweet_id`).
- `LabelTask.uri` renamed.
- Curation still special-casing `records_id_column != "uri"`.
- Feature files still writing the stored id as `uri`.
- `CHANGELOG.md` edited.
- Sibling GitHub issues 103 to 114 and 116 implemented in this PR.
