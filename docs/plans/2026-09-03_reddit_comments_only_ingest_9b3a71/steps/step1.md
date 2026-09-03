# Step 1: Write Reddit raw runs as comments only

## Goal

Stop persisting PRAW submissions. Reddit ingest still lists submissions and walks comment forests, then writes comments only.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_reddit.py` `sync_records` through `run_sync_tasks` and `fetch_records_for_subreddit`.

**Task:** open a subreddit listing, walk each submission's comments, apply eligibility filters, dedupe on `comment_fullname`, and write `comments.csv` or `comments.parquet`. Do not write a submissions file.

**Out of scope:** Bluesky and Twitter post ingest. `POSTS_FILENAME`, `parse_max_posts`, and `MAX_POSTS_KEY` in `/workspace/data_platform/ingestion/sync_checkpoint.py`. Renaming `limit_per_task`. Dump ingest. Experiments, including `fix_primary_key_column_for_reddit_posts.py`. Historical files under `/workspace/docs/plans/**`. Gitignored files under `data_platform/data/`. Operator runbooks (step 2). `CHANGELOG.md` during implementation.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-03_reddit_comments_only_ingest_9b3a71/plan.md` | Parent plan |
| `/workspace/data_platform/ingestion/sync_reddit.py` | Dual write of posts and comments. `submission_to_row`, `POSTS_RECORD_TYPE`, `include_posts`, `post_storage`, `post_row_count` |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Pattern: raise `ValueError` when the required record type is missing |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `RECORD_TYPE_FILENAMES["reddit.post"]`, `POSTS_DEDUPE_POLICY_KEY`, `COMMENTS_DEDUPE_POLICY_KEY`, `parse_max_posts` |
| `/workspace/data_platform/models/sync.py` | `SyncRedditPostModel` to delete. `SyncRedditCommentModel` already slim from issue 146 |
| `/workspace/data_platform/models/__init__.py` | Package export of `SyncRedditPostModel` |
| `/workspace/data_platform/utils/storage.py` | `RedditStorageManager.post_storage` and unused `comment_storage` |
| `/workspace/data_platform/ingestion/generate_record_id.py` | `generate_reddit_record_id` still has a `reddit_fullname` post branch |
| `/workspace/data_platform/ingestion/configs/reddit/default.yaml` | `reddit.post` in `record_types` |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml` | Same |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml` | `reddit.post` plus `posts_dedupe_policy: []` |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml` | Same as scale |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Dual-write fetch tests |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | `mock_post_row` and `reddit.post` in the minimal config |
| `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py` | `TestSubmissionToRow` |
| `/workspace/tests/data_platform/utils/test_storage.py` | `post_storage()` filename assertions |
| `/workspace/tests/data_platform/test_models_exports.py` | `SyncRedditPostModel` in expected exports |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | `posts_dedupe_policy` allowed key and scale-file assertion |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Unused `POSTS_DEDUPE_POLICY_KEY` import. `extra_fields={"post_row_count": 0}` is a generic extra-fields example, not Reddit-only |
| `/workspace/tests/data_platform/ingestion/test_generate_record_id.py` | `test_prefixes_post_fullname` uses `mock_post_row` |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/data_platform/models/__init__.py`
- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py` only to delete `"reddit.post"` from `RECORD_TYPE_FILENAMES` and delete `POSTS_DEDUPE_POLICY_KEY` if it has no remaining callers
- `/workspace/data_platform/ingestion/generate_record_id.py`
- `/workspace/data_platform/ingestion/configs/reddit/default.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`
- `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py`
- `/workspace/tests/data_platform/utils/test_storage.py`
- `/workspace/tests/data_platform/test_models_exports.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` only if the unused `POSTS_DEDUPE_POLICY_KEY` import must be removed
- `/workspace/tests/data_platform/ingestion/test_generate_record_id.py`

Plan package files under `/workspace/docs/plans/2026-09-03_reddit_comments_only_ingest_9b3a71/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/docs/runbooks/**` (step 2)
- `/workspace/data_platform/README.md` (step 2)
- `/workspace/docs/plans/**` except git commits of this work
- `/workspace/experiments/**`
- `/workspace/CHANGELOG.md` during implementation
- Any file outside the allowed list, except git commits of this work

Do not delete `POSTS_FILENAME`, `parse_max_posts`, or `MAX_POSTS_KEY`. Bluesky and Twitter still use those.

## Decision (locked)

1. A PRAW `Submission` is a fetch handle. Keep `_fetch_subreddit_page`, `_get_subreddit_listing`, `fetch_post_comments`, `is_eligible_comment`, `comments_per_post`, `min_comment_body_length`, `max_comments`, and `limit_per_task`. `limit_per_task` is how many submissions to open per subreddit, not a stored post count.
2. Delete `submission_to_row`, `POSTS_RECORD_TYPE`, `include_posts` / `include_comments` branching, `post_storage` plumbing, `post_row_count`, and `posts_collected`. Task metadata may keep `comments_collected`. Fetch stats may include `submissions_scanned` as the listing length.
3. One `RedditStorageManager` (default comments). Delete `post_storage()`. Delete `comment_storage()` because it is then redundant.
4. One `DedupeSession` on `comment_fullname`. Keep optional `comments_dedupe_policy` override through `_resolve_reddit_dedupe_policy`. Shared `dedupe_policy` is the comment skip list. Drop `posts_dedupe_policy`.
5. `record_types` must be `[reddit.comment]` only. Raise `ValueError` if `reddit.post` is present or if `reddit.comment` is missing. Copy the Bluesky missing-type error shape in `sync_bluesky.py`.
6. Delete `SyncRedditPostModel` and its package export. Delete `"reddit.post"` from `RECORD_TYPE_FILENAMES`.
7. `generate_reddit_record_id` is comments only. Drop `REDDIT_POST_RECORDS_ID_COLUMN` and the `reddit_fullname` branch. Missing `comment_fullname` raises `KeyError`.
8. `test_build_base_sync_metadata_includes_tasks` may keep `extra_fields={"post_row_count": 0}` as a generic extra-fields example. That field is not Reddit ingest metadata after this step.
9. No disk migration. Old `posts.csv` files under gitignored `data_platform/data/` stay unused.

## Contracts to lock

Add a frozen dataclass in `sync_reddit.py`:

```text
@dataclass(frozen=True)
class SubredditFetchResult:
    comment_rows: list[dict[str, Any]]
    stats: dict[str, Any]
```

`stats` keys:

```text
subreddit
listing
listing_time_filter
limit_per_subreddit
submissions_scanned
comments_collected
```

`fetch_records_for_subreddit`:

```text
fetch_records_for_subreddit(
    reddit: praw.Reddit,
    ingestion_params: dict[str, Any],
    subreddit: str,
    *,
    sync_timestamp: str,
) -> SubredditFetchResult
```

No `include_posts` or `include_comments`. On `prawcore.exceptions.NotFound`, return empty `comment_rows` and `submissions_scanned` 0, same warning as today.

`run_sync_tasks`:

```text
run_sync_tasks(
    reddit: praw.Reddit,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: RedditStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[RedditTask],
) -> None
```

One storage argument. Filenames come from `storage.records_filename`. `_open_reddit_dedupe_sessions` returns one `DedupeSession`. `_append_subreddit_deduped_rows` appends comments only and sets `metadata["row_count"]` from comment seen ids. Do not write `post_row_count`.

`init_sync_metadata` does not pass `extra_fields={"post_row_count": 0}`. `_initial_task_progress` has `comments_collected` and does not have `posts_collected`.

`sync_records` constructs one `RedditStorageManager` after `ensure_dataset_manifest`. It does not call `post_storage()`. It raises if `reddit.post` is in `record_types` or if `reddit.comment` is not.

Delete these symbols:

- `submission_to_row`
- `POSTS_RECORD_TYPE` in `sync_reddit.py`
- `SyncRedditPostModel`
- `RedditStorageManager.post_storage`
- `RedditStorageManager.comment_storage`
- `RECORD_TYPE_FILENAMES["reddit.post"]`
- `POSTS_DEDUPE_POLICY_KEY` when unused
- `REDDIT_POST_RECORDS_ID_COLUMN`

YAML for all four Reddit configs:

- `record_types: [reddit.comment]`
- no `posts_dedupe_policy`

## Test design

One test class per function where the file already uses that pattern. Use `data_root`. Prefer public `run_sync_tasks`, `sync_records`, and `fetch_records_for_subreddit`.

Drop `mock_post_row` from `/workspace/tests/data_platform/ingestion/reddit_conftest.py`. Minimal config `record_types` is `[sync_reddit.COMMENTS_RECORD_TYPE]` only. Drop `posts_dedupe_policy` from the fixture. Keep `comments_dedupe_policy` on the fixture so override coverage stays.

Rewrite `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` so fake fetch returns `SubredditFetchResult`. No `post_storage`, `include_posts`, `include_comments`, `mock_post_row`, `post_row_count`, or `reddit.post` skip counters. Delete `test_run_sync_tasks_empty_posts_override_does_not_skip_prior_posts`.

```text
given two subreddits each returning one comment
when run_sync_tasks runs
then metadata row_count is 2
and run_dir / comments.csv exists
and run_dir / posts.csv does not exist
and comment_fullname seen ids has two ids

given max_comments 1 and two subreddit tasks
when run_sync_tasks runs
then row_count is 1
and the second task is skipped

given a prior comment id on this dataset and shared or comments skip list with prior_runs_same_dataset
when run_sync_tasks fetches that id plus a new id
then only the new id is written
and rows_skipped_as_duplicates is 1 keyed by reddit.comment

given reddit.post in record_types
when sync_records runs
then raise ValueError

given record_types without reddit.comment
when sync_records runs
then raise ValueError

given parquet dataset.json
when run_sync_tasks writes
then comments.parquet exists
and posts.parquet does not exist

given sync_records config with output_format parquet
when sync_records runs with mocked client and run_sync_tasks
then run_sync_tasks receives one storage whose records_filename is comments.parquet
and the call has no post_storage argument

given ingestion_params limit_per_task 1
when fetch_records_for_subreddit runs
then _fetch_subreddit_page is called with limit 1
```

Other tests:

- `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py`: delete `TestSubmissionToRow`, `_mock_submission`, and the `submission_to_row` / `SyncRedditPostModel` imports. Keep `TestCommentToRow`.
- `/workspace/tests/data_platform/utils/test_storage.py`: `TestRedditStorageManagerRecordsFilename` asserts default `comments.csv` and parquet `comments.parquet` only. Do not call `post_storage()`.
- `/workspace/tests/data_platform/test_models_exports.py`: expected exports are `SyncBlueskyPostModel`, `SyncRedditCommentModel`, `SyncTwitterPostModel`.
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`: drop `posts_dedupe_policy` from `DEDUPE_POLICY_KEYS` and `REDDIT_TYPE_DEDUPE_POLICY_KEYS`. Scale-file test asserts shared `dedupe_policy` and no `posts_dedupe_policy`. Add that every Reddit YAML `record_types` is exactly `[reddit.comment]`.
- `/workspace/tests/data_platform/ingestion/test_generate_record_id.py`: delete `test_prefixes_post_fullname`. Missing-fields case raises `KeyError` for `comment_fullname`. Drop `mock_post_row` import.
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`: drop unused `POSTS_DEDUPE_POLICY_KEY` import. Leave `test_record_type_to_filename_known_types` as Bluesky post, Reddit comment, and unknown fallback. Leave `extra_fields={"post_row_count": 0}` on `test_build_base_sync_metadata_includes_tasks`.

## Implementation notes (implement-from-spec)

Files already exist. This is a deletion refactor. Do not add a second ingest path beside the old one.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `SubredditFetchResult`. Change `fetch_records_for_subreddit` and `run_sync_tasks` signatures to the contracts above. Bodies of those two functions and of `_open_reddit_dedupe_sessions` / `_append_subreddit_deduped_rows` / `sync_records` record-type checks may raise `NotImplementedError` or keep a thin call shape without writing posts. Do not delete `SyncRedditPostModel` yet if that would make imports fail before tests are rewritten. Prefer keeping imports resolving.
3. Phase 3 contracts. Lock the signatures in this file. Full auto. Do not wait for approval.
4. Phase 4 test design. Rewrite the tests listed above so they describe comments-only behavior. They must fail for `NotImplementedError` or still-present post writes, not for missing imports.
5. Phase 5 units, in this order, one commit each:
   1. Committed Reddit YAML: `record_types: [reddit.comment]`, drop `posts_dedupe_policy`. YAML tests that only read files start passing.
   2. Delete `SyncRedditPostModel` and its package export. `test_models_exports` passes.
   3. Delete `post_storage()` and `comment_storage()`. Storage filename tests pass.
   4. Delete `"reddit.post"` from `RECORD_TYPE_FILENAMES`. Delete `POSTS_DEDUPE_POLICY_KEY` if unused. Drop it from checkpoint tests.
   5. Comments-only `generate_reddit_record_id`. Record-id tests pass.
   6. Implement comments-only `fetch_records_for_subreddit` (listing fetch plus comment forest, no `submission_to_row`).
   7. Implement comments-only dedupe, append, `run_sync_tasks`, and `sync_records` record-type validation. Delete leftover post symbols.
6. Phase 6. Run the must-pass commands.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ -q
```

Expected: exit 0.

Also, after Phase 5 unit 7:

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_reddit_checkpoint.py tests/data_platform/ingestion/test_raw_row_timestamps.py tests/data_platform/utils/test_storage.py tests/data_platform/test_models_exports.py tests/data_platform/ingestion/test_ingest_yaml_keys.py tests/data_platform/ingestion/test_generate_record_id.py tests/data_platform/ingestion/test_sync_checkpoint.py -q
```

Expected: exit 0.

## Must fail / not happen

- New Reddit raw runs write `posts.csv` or `posts.parquet`.
- `SyncRedditPostModel` or `post_storage()` still exist.
- Committed Reddit YAML still lists `reddit.post` or `posts_dedupe_policy`.
- Listing fetch or comment-forest walk removed.
- `limit_per_task` renamed.
- Bluesky or Twitter product code changed.
- `parse_max_posts` / `MAX_POSTS_KEY` / `POSTS_FILENAME` deleted.
- Preprocess, feature, or curate Reddit behavior changed.
- Dump ingest implemented.
- Historical `docs/plans/**` edited.
- Experiments edited.
- Gitignored `data_platform/data/` migrated.
