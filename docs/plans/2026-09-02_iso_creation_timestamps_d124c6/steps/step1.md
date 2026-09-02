# Step 1: Write ISO creation times and drop the leftover Reddit column

## Goal

Write UTC ISO-8601 `created_at` on new Twitter and Reddit raw rows. Stop writing Reddit `created_utc` on those rows and on the Reddit sync models. Leave Bluesky `created_at` and stimuli sampling unchanged.

## Caller / unit of work

**Main callers:**

- `data_platform/ingestion/twitter_client.py` `tweet_to_row`, reached from `fetch_posts_for_keyword` through `_append_tweets_from_response`
- `data_platform/ingestion/sync_reddit.py` `submission_to_row` and `comment_to_row`, reached from `fetch_records_for_subreddit` and `fetch_post_comments`

**Task:** store payload creation time as UTC ISO-8601 in `created_at`, and omit `created_utc` from Reddit rows and models.

**Out of scope:** Bluesky writer changes. Stimuli sampling (GitHub issue 113). Canonical author fields (114). Source record id (115). Preprocess length and language gates (116). Adding a new function in `lib/timestamp_utils.py`. Rewriting completed run files. Experiment dump code under `experiments/`. `CHANGELOG.md`. Sibling GitHub issues 103 to 111 and 113 to 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/lib/timestamp_utils.py` | Current-time helper only. Format is `%Y_%m_%d-%H:%M:%S`. Do not use it for row `created_at`. Do not add another generator. |
| `/workspace/data_platform/ingestion/twitter_client.py` | `tweet_to_row` currently writes `str(tweet.created_at)`. |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `submission_to_row` and `comment_to_row` already call `.isoformat()` for `created_at`, and they also write `created_utc` with the same string. PRAW input field `created_utc` stays as the unix source. |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Already writes payload `created_at`. Do not change it. |
| `/workspace/data_platform/models/sync.py` | `SyncRedditPostModel` and `SyncRedditCommentModel` still require `created_utc`. `PreprocessedRedditCommentModel` inherits the comment model. |
| `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py` | Twitter uses `fromisoformat`, which accepts a space-separated string. Reddit asserts the leftover alias. |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | Mock rows still include `created_utc`. Storage validates against the sync models (`extra="forbid"`). |
| `/workspace/data_platform/utils/storage.py` | Reddit writers validate rows with `SyncRedditPostModel` and `SyncRedditCommentModel`. |

## Files allowed to change

- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`

Plan package files under `/workspace/docs/plans/2026-09-02_iso_creation_timestamps_d124c6/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/lib/timestamp_utils.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/experiments/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Twitter `tweet_to_row` `created_at` rules:

- If `tweet.created_at` is present, write `tweet.created_at.isoformat()`.
- If `tweet.created_at` is missing or false, write `""`.
- Do not use `str(tweet.created_at)`.
- Do not call `get_current_timestamp` for this field. That helper is for current run time, not payload creation time.

Reddit `submission_to_row` and `comment_to_row` rules:

- Keep `created_at = datetime.fromtimestamp(..., tz=timezone.utc).isoformat()`.
- Keep reading PRAW `post.created_utc` and `comment.created_utc` as the unix input.
- Do not include `created_utc` in the output dict.

Reddit model rules in `data_platform/models/sync.py`:

- `SyncRedditPostModel` has `created_at: str` and does not declare `created_utc`.
- `SyncRedditCommentModel` has `created_at: str` and does not declare `created_utc`.
- `PreprocessedRedditCommentModel` stays a subclass of `SyncRedditCommentModel`. Do not re-add `created_utc` there.
- Models keep `extra="forbid"`, so a leftover `created_utc` key on a new row is invalid.

Keep these signatures unchanged:

```text
tweet_to_row(tweet, *, username: str, keyword: str, sync_timestamp: str) -> dict[str, object]
submission_to_row(post, sync_timestamp: str) -> dict[str, Any]
comment_to_row(comment, submission, sync_timestamp: str, *, depth: int, comment_rank: int) -> dict[str, Any]
```

Do not add a shared ISO helper. Do not add a function in `lib/timestamp_utils.py`.

## Test design

Prefer the public row writers. One test class per function. Keep the Bluesky test as a regression that the payload `created_at` and run `sync_timestamp` still land.

```text
given a tweet with created_at datetime(2026, 5, 30, tzinfo=timezone.utc)
when tweet_to_row(...)
then result["created_at"] == "2026-05-30T00:00:00+00:00"
and result["sync_timestamp"] == SYNC_TIMESTAMP
and SyncTwitterPostModel.model_validate(result) succeeds

given a tweet with created_at None
when tweet_to_row(...)
then result["created_at"] == ""

given a PRAW submission whose created_utc unix time is 2026-05-30 UTC
when submission_to_row(...)
then result["created_at"] == "2026-05-30T00:00:00+00:00"
and "created_utc" not in result
and result["sync_timestamp"] == SYNC_TIMESTAMP
and SyncRedditPostModel.model_validate(result) succeeds

given a PRAW comment whose created_utc unix time is 2026-05-30 UTC
when comment_to_row(...)
then result["created_at"] == "2026-05-30T00:00:00+00:00"
and "created_utc" not in result
and result["sync_timestamp"] == SYNC_TIMESTAMP
and SyncRedditCommentModel.model_validate(result) succeeds

given a Bluesky search hit whose payload created_at is 2026-05-30T00:00:00.000Z
when fetch_posts_for_keyword(...)
then rows[0]["created_at"] == "2026-05-30T00:00:00.000Z"
and rows[0]["sync_timestamp"] == SYNC_TIMESTAMP
```

Rename the Reddit tests so they no longer say they keep a `created_utc` alias. Replace the Twitter `fromisoformat` assertion with an exact ISO string. Drop `created_utc` from `mock_comment_row` and `mock_post_row` in the same test-design commit so storage validation matches the new models.

## Implementation notes (implement-from-spec)

Files already exist. Do not add a new timestamp helper. Scaffold and contracts are edits to existing writers and models.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm callers, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Update `tweet_to_row`, `submission_to_row`, and `comment_to_row` docstrings so they state ISO `created_at` and that Reddit output has no `created_utc`. Leave runtime behavior unchanged. Existing tests stay green.
3. Phase 3 contracts. Remove `created_utc` from `SyncRedditPostModel` and `SyncRedditCommentModel`. Bodies of the row writers still emit `created_utc`. Full auto. Do not wait for approval. Reddit tests that validate rows fail until later phases because `extra="forbid"`.
4. Phase 4 test design. Update `test_raw_row_timestamps.py` and drop `created_utc` from `reddit_conftest.py` fixtures. Twitter exact-ISO and missing-created_at tests fail until Phase 5. Reddit tests fail until the writers stop emitting `created_utc`. Checkpoint tests that use the fixtures should go green once the fixtures match the models.
5. Phase 5 units, in this order, one commit each:
   1. In `tweet_to_row`, write `tweet.created_at.isoformat()` when present, else `""`. Twitter tests pass. Reddit tests stay red.
   2. Remove `created_utc` from `submission_to_row` and `comment_to_row` output dicts. Reddit timestamp tests pass.
6. Phase 6. Run the must-pass commands. Confirm Bluesky is unchanged. Confirm `lib/timestamp_utils.py` is unchanged. Confirm no `created_utc` key on new Reddit rows.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_raw_row_timestamps.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures.

## Must fail / not happen

- `str(tweet.created_at)` on new Twitter rows.
- `created_utc` present on new Reddit post or comment rows.
- `created_utc` declared on `SyncRedditPostModel` or `SyncRedditCommentModel`.
- A new helper in `lib/timestamp_utils.py`.
- Bluesky writer changes.
- Stimuli sampling changes.
- `CHANGELOG.md` edited.
- Experiment YAML or dump code under `experiments/` edited.
- Sibling GitHub issues 103 to 111 and 113 to 116 implemented in this PR.
