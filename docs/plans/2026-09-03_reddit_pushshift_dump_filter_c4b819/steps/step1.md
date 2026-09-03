# Step 1: Read dump comments, drop deleted or removed, map onto the ingest model

## Goal

Stream comments from a compressed dump JSONL file, drop deleted or removed comments, and map keepers onto the same Reddit comment ingest model used by live Reddit ingest. Do not sample and do not write parquet.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/reddit/transform.py` `dump_comment_to_sync_row`, reached from tests in this step and from the Step 2 file processor.

**Task:** prove read → drop deleted or removed → map to a dict that `SyncRedditCommentModel.model_validate` accepts.

**Out of scope:** Reservoir sampling. Parquet write. CLI. Gitignore. Runbook path update. Live PRAW ingest. Changing `SyncRedditCommentModel`. Editing `data_platform/ingestion/data_dumps/reddit/README.md`. The old toxicity experiment. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/data_dumps/reddit/README.md` | Spec. Do not edit. Deleted-or-removed rule, month files, ingest-model requirement |
| `/workspace/data_platform/models/sync.py` | `SyncRedditCommentModel` field list, `extra="forbid"` |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `comment_to_row` UTC ISO `created_at` conversion. Copy the timestamp conversion, not PRAW objects |
| `/workspace/data_platform/ingestion/generate_record_id.py` | `attach_record_id(row, "reddit")` / `generate_reddit_record_id` |
| `/workspace/lib/timestamp_utils.py` | `get_current_timestamp` is for run timestamps in Step 2. Do not add another generator |
| `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/reader.py` | zstd JSONL stream pattern to copy, not import |
| `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/filters.py` | Deleted tokens `{[deleted], [removed]}`. Do not copy toxicity, length, AutoModerator, or subreddit filters |
| `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/transform.py` | `link_id` prefix strip, `t1_{id}` fullname, permalink fallback. Do not copy Chicago timestamps or parent-tree depth |
| `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/tests/test_reader.py` | Tiny zst fixture helper |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | Example live comment row shape |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/models.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/reader.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/filters.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/transform.py`
- `/workspace/tests/data_platform/ingestion/test_reddit_data_dump.py`

Plan package files under `/workspace/docs/plans/2026-09-03_reddit_pushshift_dump_filter_c4b819/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/README.md`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/models/sync.py`
- `/workspace/data_platform/ingestion/generate_record_id.py`
- `/workspace/lib/timestamp_utils.py`
- `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add `DumpCommentRaw` in `models.py` with `extra="ignore"` so extra dump JSON keys are dropped:

```text
id: str
author: str
link_id: str
parent_id: str
subreddit: str
body: str
score: int
created_utc: int
permalink: str | None = None
```

Add `iter_dump_comments(input_path: Path) -> Iterator[DumpCommentRaw]` in `reader.py`.

- Open the path as zstd-compressed JSONL, same stream approach as `experiments/fetch_reddit_pushshift_dump_2026_06_15/reader.py` `iter_pushshift_comments`.
- Skip blank lines, invalid JSON, and rows that fail `DumpCommentRaw` validation. Do not raise on a bad line.
- Raise `FileNotFoundError` when the path is not a file.

Add `DELETED_BODY_OR_AUTHOR_TOKENS = frozenset({"[deleted]", "[removed]"})` and `keep_dump_comment(comment: DumpCommentRaw) -> bool` in `filters.py`.

- Return False when `comment.author.strip()` is in the token set.
- Return False when `comment.body.strip()` is in the token set.
- Return True otherwise, including short or empty bodies that are not those tokens.
- Do not filter AutoModerator, subreddit, or body length.

Add `dump_comment_to_sync_row(comment: DumpCommentRaw, sync_timestamp: str) -> dict[str, object]` in `transform.py`.

- `post_reddit_id` = `comment.link_id` with a leading `t3_` removed.
- `post_reddit_fullname` = `comment.link_id`.
- `subreddit` = `comment.subreddit`.
- `comment_id` = `comment.id`.
- `comment_fullname` = `t1_{comment.id}`.
- `parent_id` = `comment.parent_id`.
- `author` = `comment.author`.
- `body` = `comment.body`.
- `score` = `comment.score`.
- `created_at` = `datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat()`. Same conversion as `comment_to_row` in `sync_reddit.py`. Do not write `created_utc`.
- `permalink` = `comment.permalink` when present and non-empty. Otherwise synthesize `/r/{subreddit}/comments/{post_reddit_id}/_/{comment_id}/`. If a provided permalink does not start with `/`, prefix `/`.
- `depth` = 0 when `parent_id` starts with `t3_`, else 1. Do not walk parent chains.
- `comment_rank` = 0.
- `sync_timestamp` = the argument.
- Return `attach_record_id(row, INTEGRATION_REDDIT)` so `record_id` is `reddit_{post_reddit_id}_{comment_id}`.
- The returned dict must pass `SyncRedditCommentModel.model_validate`.

Numpy docstrings on the public functions. Module docstrings include the `PYTHONPATH=. uv run python ...` run line for files that are runnable later. Reader, filter, and transform modules are importable libraries; their module docstrings state purpose only.

Do not import from `experiments/`.

## Test design

One test class per public function. Build tiny `.zst` fixtures in `tmp_path` the same way as `test_iter_pushshift_comments_reads_fixture`. Use a shared helper in the test file to build `DumpCommentRaw` objects. Patch nothing in Step 1 except where a test needs a missing file.

```text
given a zst JSONL file with one valid dump comment
when iter_dump_comments(path)
then yield one DumpCommentRaw with that id

given a zst JSONL file with a blank line, invalid JSON, and one valid comment
when iter_dump_comments(path)
then yield only the valid comment

given a path that is not a file
when iter_dump_comments(path)
then raise FileNotFoundError

given author "user" and body "hello"
when keep_dump_comment(comment)
then True

given author "[deleted]"
when keep_dump_comment(comment)
then False

given body "[removed]"
when keep_dump_comment(comment)
then False

given body "  [deleted]  "
when keep_dump_comment(comment)
then False

given body "short"
when keep_dump_comment(comment)
then True

given a top-level dump comment with permalink and created_utc 1748736018
when dump_comment_to_sync_row(comment, "2026_09_03-12:00:00")
then SyncRedditCommentModel.model_validate(result) succeeds
and post_reddit_id is link_id without t3_
and comment_fullname is t1_{id}
and record_id is reddit_{post_reddit_id}_{comment_id}
and created_at is UTC ISO-8601 from the unix time
and created_utc is not a key
and depth is 0
and comment_rank is 0
and sync_timestamp is the argument

given a nested comment whose parent_id starts with t1_
when dump_comment_to_sync_row(...)
then depth is 1

given permalink missing
when dump_comment_to_sync_row(...)
then permalink is the synthesized /r/{subreddit}/comments/{post_id}/_/{comment_id}/ path
```

## Implementation notes (implement-from-spec)

Files do not exist yet. Scaffold means adding the four modules with public functions that `raise NotImplementedError`, plus an empty test module that imports them.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add the four modules with stub bodies and numpy docstrings. Add the test file with imports only. Commit.
3. Phase 3 contracts. Confirm signatures and `DumpCommentRaw` fields match the freeze. Bodies stay stubs. Full auto. Commit only if signatures change.
4. Phase 4 test design. Add the tests from the pseudocode. They must fail for `NotImplementedError`. Commit.
5. Phase 5 units, in this order, one commit each:
   1. Implement `DumpCommentRaw` and `iter_dump_comments`. Reader tests pass.
   2. Implement `keep_dump_comment`. Filter tests pass. Reader tests stay green.
   3. Implement `dump_comment_to_sync_row`. All Step 1 tests pass.
6. Phase 6. Run the must-pass command. Confirm README, `sync_reddit.py`, and `SyncRedditCommentModel` are untouched.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_reddit_data_dump.py -q
```

Expected: exit 0.

## Must fail / not happen

- `README.md` in the dump directory edited.
- `sync_reddit.py` or `SyncRedditCommentModel` edited.
- Import from `experiments/fetch_reddit_pushshift_dump_2026_06_15`.
- Toxicity, length, AutoModerator, or extra subreddit filters.
- Sampling or parquet write in this step.
- `created_utc` present on mapped rows.
- Parent-tree depth walking.
