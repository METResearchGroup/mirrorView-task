# Step 1: Copy shared author handle during preprocess

## Goal

Give every preprocessed row a shared `author_handle` column without renaming raw ingest author fields. Copy `author_id` through only when the raw row already has it.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/runner.py` `preprocess_records`, reached from `preprocess_bluesky.py`, `preprocess_reddit.py`, and `preprocess_twitter.py`.

**Task:** after `add_canonical_text_column`, call `add_canonical_author_columns`. Validate the extra preprocessed columns with the existing storage model swap.

**Out of scope:** Raw ingest writers and `Sync*` field lists. Source record id (GitHub issue 115). Stimuli sampling. Length and language gates (116). Joining or filtering on `author_handle` in feature or curate code. `CHANGELOG.md`. Sibling GitHub issues 103 to 113 and 115 to 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/runner.py` | `add_canonical_text_column`, `preprocess_records`, `AUTHOR_COLUMN`, `PreprocessPlatformSpec` |
| `/workspace/data_platform/preprocessing/preprocess_bluesky.py` | `BLUESKY_SPEC` already matches shared handle |
| `/workspace/data_platform/preprocessing/preprocess_reddit.py` | `REDDIT_SPEC`, row validators on native `author` |
| `/workspace/data_platform/preprocessing/preprocess_twitter.py` | `TWITTER_SPEC` |
| `/workspace/data_platform/models/sync.py` | `PreprocessedRedditCommentModel` already adds `text` |
| `/workspace/data_platform/utils/storage.py` | Reddit swaps model on `StorageStage.PREPROCESSED` |
| `/workspace/data_platform/utils/platform_specific_columns.py` | `CANONICAL_TEXT_COLUMN` pattern |
| `/workspace/tests/data_platform/preprocessing/test_add_canonical_text_column.py` | Helper test shape |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` | End-to-end preprocess assertions |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py` | End-to-end preprocess assertions |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Bluesky preprocess coverage |
| `/workspace/data_platform/generate_features/generate_twitter_features.py` | Loads preprocessed rows with `SyncTwitterPostModel` (`extra="forbid"`) |
| `/workspace/tests/data_platform/generate_features/test_generate_reddit_features.py` | Sample preprocessed comments need `author_handle` once the model requires it |
| `/workspace/tests/data_platform/generate_features/test_generate_twitter_features.py` | Sample preprocessed posts need `author_handle` once the Twitter preprocessed model is used |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function. Arrange, act, assert. |

## Files allowed to change

- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py` (spec fields only)
- `/workspace/data_platform/preprocessing/preprocess_reddit.py` (spec fields only)
- `/workspace/data_platform/preprocessing/preprocess_twitter.py` (spec fields only)
- `/workspace/data_platform/models/sync.py` (`PreprocessedRedditCommentModel`, new `PreprocessedTwitterPostModel`)
- `/workspace/data_platform/utils/platform_specific_columns.py`
- `/workspace/data_platform/utils/storage.py` (Twitter preprocessed model on `StorageStage.PREPROCESSED`)
- `/workspace/data_platform/generate_features/generate_twitter_features.py` (`model_cls` only, so load validation accepts the new column)
- `/workspace/tests/data_platform/preprocessing/test_add_canonical_author_columns.py` (new)
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py`
- `/workspace/tests/data_platform/generate_features/test_generate_reddit_features.py` (fixture column only)
- `/workspace/tests/data_platform/generate_features/test_generate_twitter_features.py` (fixture column only)

Plan package files under `/workspace/docs/plans/2026-09-02_shared_author_fields_764448/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/**`
- Field lists on `SyncBlueskyPostModel`, `SyncRedditCommentModel`, `SyncRedditPostModel`, `SyncTwitterPostModel`
- `/workspace/data_platform/curate/**` except if a test assertion names the preprocessed schema
- Stimuli sampling under `/workspace/experiments/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add this constant in `/workspace/data_platform/utils/platform_specific_columns.py`:

```text
CANONICAL_AUTHOR_HANDLE_COLUMN = "author_handle"
```

Do not add an `author_id` constant. Do not add `preprocessed_model_cls` on `PreprocessPlatformSpec`. Storage already validates on write.

`PreprocessPlatformSpec` gains:

```text
author_handle_source_column: str | None = None
```

- `None` means the frame already has `author_handle` (Bluesky). Require that column. Do not overwrite values.
- `"author"` for Reddit. `"username"` for Twitter.

```text
add_canonical_author_columns(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame
```

- Returns a new frame. Does not mutate input.
- When `author_handle_source_column` is set, require that column, set `author_handle` to `str` of the source, and keep the source column.
- Do not add `author_id` unless it is already on the input frame.
- Raise `KeyError` when the required source or passthrough column is missing.

`preprocess_records` order:

```text
records = add_canonical_text_column(records, spec)
records = add_canonical_author_columns(records, spec)
```

Then `apply_text_transform`, `filter_records`, and `save_preprocessed` stay as they are.

Reddit `filter_records` / `check_if_not_automoderator` still read native `author`, not `author_handle`.

Models in `/workspace/data_platform/models/sync.py`:

```text
PreprocessedRedditCommentModel(SyncRedditCommentModel):
  text: str
  author_handle: str

PreprocessedTwitterPostModel(SyncTwitterPostModel):
  author_handle: str
```

Bluesky needs no new model. `SyncBlueskyPostModel` already declares `author_handle`.

`TwitterStorageManager` uses `PreprocessedTwitterPostModel` when `stage == StorageStage.PREPROCESSED`, the same way Reddit already swaps to `PreprocessedRedditCommentModel`.

`generate_twitter_features.TWITTER_SPEC.model_cls` becomes `PreprocessedTwitterPostModel`. Do not read `author_handle` for joins or filters.

Platform spec wiring:

- Bluesky: `author_handle_source_column=None`
- Reddit: `author_handle_source_column="author"`
- Twitter: `author_handle_source_column="username"`

When `filter_comments` or `filter_posts` rebuilds a spec, copy `author_handle_source_column` from the platform spec.

## Test design

Location: `/workspace/tests/data_platform/preprocessing/test_add_canonical_author_columns.py`

Import `add_canonical_author_columns` from `data_platform.preprocessing.runner`. One class: `TestAddCanonicalAuthorColumns`.

Use `mock_comment_row`, `mock_tweet_row`, and `make_post_row`.

```text
given a Reddit frame with author="regular_user"
when add_canonical_author_columns(..., REDDIT_SPEC)
then author_handle equals "regular_user"
and author is unchanged
and author_id is not in the result columns
and author_handle is not on the input frame

given a Twitter frame with username="handle" and author_id="123"
when add_canonical_author_columns(..., TWITTER_SPEC)
then author_handle equals "handle"
and username and author_id are unchanged

given a Bluesky frame with author_handle="a.bsky.social"
when add_canonical_author_columns(..., BLUESKY_SPEC)
then author_handle is unchanged
and author_id is not in the result columns

given a Reddit frame missing author
when add_canonical_author_columns(..., REDDIT_SPEC)
then raise KeyError

given a Bluesky frame missing author_handle
when add_canonical_author_columns(..., BLUESKY_SPEC)
then raise KeyError
```

Extend end-to-end preprocess tests. Reload through `StorageManager(StorageStage.PREPROCESSED, ...)`:

- Reddit `test_preprocess_records_writes_output`: saved row has `author_handle == author` and no `author_id` column.
- Twitter `test_preprocess_records_writes_output`: saved row has `author_handle == username` and `author_id` preserved.
- Bluesky `test_preprocessed_rows_include_text`: also assert `author_handle` equals the raw value and `author_id` is absent.

Update feature-generation sample rows so they include `author_handle` copied from the native handle. Do not change feature or curate production logic beyond the Twitter `model_cls` swap.

## Implementation notes (implement-from-spec)

The text helper already exists. Scaffold a stub author helper. Full auto. Do not wait for approval.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm callers, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `add_canonical_author_columns` that raises `NotImplementedError`. Add `/workspace/tests/data_platform/preprocessing/test_add_canonical_author_columns.py` with the import and an empty `TestAddCanonicalAuthorColumns` class. Do not call the helper from `preprocess_records` yet.
3. Phase 3 contracts. Add `CANONICAL_AUTHOR_HANDLE_COLUMN`, `author_handle_source_column` on the spec (default `None`), the helper signature and docstring, `author_handle` on `PreprocessedRedditCommentModel`, and `PreprocessedTwitterPostModel`. Helper body still raises `NotImplementedError`. Full auto.
4. Phase 4 test design. Add the failing helper tests and the end-to-end assertions. Add `author_handle` on Reddit and Twitter feature sample rows. Helper tests fail because of `NotImplementedError`.
5. Phase 5 units, in this order, one commit each:
   1. Implement `add_canonical_author_columns`. Helper tests pass once specs name the source columns. End-to-end preprocess tests stay red until the caller is wired.
   2. Set `author_handle_source_column` on Reddit and Twitter specs, and copy it when those modules rebuild a spec.
   3. Call `add_canonical_author_columns` from `preprocess_records` after the text helper.
   4. Swap Twitter preprocessed storage and Twitter feature `model_cls` to `PreprocessedTwitterPostModel`. End-to-end preprocess tests pass.
6. Phase 6. Run the must-pass commands. Confirm ingest writers are unchanged. Confirm no `author_id` on Bluesky or Reddit preprocessed output. Confirm `CHANGELOG.md` is unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0 with no new failures outside preprocessing. Three `opik_enabled` failures in `tests/data_platform/generate_features/test_platform_cli.py` are pre-existing.

## Must fail / not happen

- Raw ingest writers renamed or duplicated (`author` rewritten to `author_handle` at sync time).
- `author_id` column added to Bluesky or Reddit preprocessed output.
- `author_handle` added to any `Sync*` model except the existing Bluesky field.
- Reddit row validators reading `author_handle` instead of `author`.
- Feature or curate code joining or filtering on `author_handle`.
- `source_record_id` or GitHub issue 115 work bundled here.
- `CHANGELOG.md` edited.
- Sibling GitHub issues 103 to 113 and 115 to 116 implemented in this PR.
