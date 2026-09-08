# Step 10: Write ISO creation timestamps and drop Reddit’s duplicate utc column

## Goal

All three ingest platforms write UTC ISO-8601 `created_at` at raw row write. Twitter currently uses `str(tweet.created_at)`, which yields a space-separated datetime string, not ISO. Reddit duplicates the same ISO value under both `created_at` and `created_utc`; drop the redundant column from raw rows and sync models.

## Caller / unit of work

**Main callers:** `tweet_to_row` in `data_platform/ingestion/twitter_client.py`; `submission_to_row` / `comment_to_row` in `data_platform/ingestion/sync_reddit.py`; `_posts_to_rows` in `data_platform/ingestion/sync_bluesky.py`.

**Slice:** normalize `created_at` at row construction → update Reddit/Twitter sync models → align timestamp tests and Reddit fixtures.

**Out of scope:** `sync_timestamp` format (`get_current_timestamp`), platform-native id column names, preprocess/features/curate, YAML configs, other plan steps.

## Decision (locked)

- **Canonical raw creation field:** `created_at` as UTC ISO-8601 string.
- **Twitter:** `tweet_to_row` must use `datetime.isoformat()` (with timezone) when `tweet.created_at` is set. Do **not** use `str(tweet.created_at)`.
- **Reddit:** keep converting PRAW `created_utc` (Unix float) via `datetime.fromtimestamp(..., tz=timezone.utc).isoformat()` into `created_at`. Remove `created_utc` from post and comment row dicts and from `SyncRedditPostModel` / `SyncRedditCommentModel` in `data_platform/models/sync.py`.
- **Bluesky:** `_posts_to_rows` already passes through API `post.record.created_at` (e.g. `2026-05-30T00:00:00.000Z`). No change required if the value already parses as UTC ISO; do not reformat unnecessarily.
- **`sync_timestamp`:** unchanged — still `get_current_timestamp` format on every row.
- **Independently shippable:** one PR; do not rename platform id columns (`tweet_id`, `reddit_id`, `uri`, etc.).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 10 |
| `data_platform/ingestion/twitter_client.py` | `tweet_to_row` uses `str(tweet.created_at)` today |
| `data_platform/ingestion/sync_reddit.py` | `submission_to_row` / `comment_to_row` write duplicate `created_utc` |
| `data_platform/ingestion/sync_bluesky.py` | `_posts_to_rows` passes API `created_at` |
| `data_platform/models/sync.py` | `SyncRedditPostModel` / `SyncRedditCommentModel` include `created_utc` |
| `tests/data_platform/ingestion/test_raw_row_timestamps.py` | Platform timestamp assertions and model validation |
| `tests/data_platform/ingestion/reddit_conftest.py` | `mock_comment_row` / `mock_post_row` include `created_utc` |
| `tests/data_platform/ingestion/conftest.py` | Bluesky `mock_post` `created_at` shape |

## Files allowed to change

- `data_platform/ingestion/twitter_client.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/models/sync.py` (Reddit sync models only)
- `tests/data_platform/ingestion/test_raw_row_timestamps.py`
- `tests/data_platform/ingestion/reddit_conftest.py`
- `CHANGELOG.md` (after the PR exists, via write-changelog)

## Files forbidden to change

- `data_platform/ingestion/sync_bluesky.py` (unless Bluesky `created_at` is found not to be UTC ISO — then minimal fix only)
- Preprocess, features, curate, stimuli
- All YAML under `data_platform/ingestion/configs/`
- `lib/timestamp_utils.py` / `get_current_timestamp`
- Platform id column names on raw rows

## Contracts

```text
tweet_to_row(...)
  created_at: tweet.created_at.isoformat() when tweet.created_at is truthy, else ""
  Must contain "T" between date and time (ISO-8601), not a space from str(datetime).

submission_to_row(...) / comment_to_row(...)
  created_at: datetime.fromtimestamp(praw_created_utc, tz=timezone.utc).isoformat()
  Row dict must NOT include "created_utc".
  sync_timestamp unchanged.

_posts_to_rows(...)  [Bluesky, verify only]
  created_at: post.record.created_at (API string, UTC ISO with Z suffix acceptable)

SyncRedditPostModel / SyncRedditCommentModel
  Fields include created_at: str; do NOT include created_utc.
  PreprocessedRedditCommentModel inherits from SyncRedditCommentModel — no separate created_utc field.
```

## Tests (write first)

Update `tests/data_platform/ingestion/test_raw_row_timestamps.py`:

- **Bluesky** (`TestFetchPostsForKeyword`): keep asserting ISO `created_at` and `sync_timestamp`; `SyncBlueskyPostModel.model_validate` still passes.
- **Reddit** (`TestSubmissionToRow`, `TestCommentToRow`): assert ISO `created_at` and `sync_timestamp`; assert `"created_utc" not in result`; rename tests to drop “keeps created_utc alias”; `SyncRedditPostModel` / `SyncRedditCommentModel` validation still passes.
- **Twitter** (`TestTweetToRow`): assert `created_at` contains `"T"` (ISO separator); `datetime.fromisoformat(str(result["created_at"]))` round-trips to the source datetime; assert `str(created_at)` space-separated form is **not** produced (e.g. `"2026-05-30 00:00:00" not in result["created_at"]`); `SyncTwitterPostModel.model_validate` still passes.

Update `tests/data_platform/ingestion/reddit_conftest.py`: remove `created_utc` from `mock_comment_row` and `mock_post_row`.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per function.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_raw_row_timestamps.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0. No new failures.

## Must not happen

- Changing `sync_timestamp` format or source.
- Renaming platform-native id columns (`tweet_id`, `reddit_id`, `comment_id`, `uri`, etc.).
- Adding `created_utc` back as an alias anywhere in raw ingest or sync models.
- Twitter `created_at` using `str(datetime)` (space-separated).
- Touching preprocess, features, curate, or ingest YAML in this PR.
