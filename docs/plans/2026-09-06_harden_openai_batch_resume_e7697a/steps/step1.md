# Step 1: Persist provider job state, parse partial batch results, retry only transient failures, and complete on exact id coverage

## Goal

Make one OpenAI Batch labeling chunk survive a process crash without a second provider job, keep the successful rows of a partly failed provider batch, retry only transient failures up to four attempts per record, and mark a feature complete only when every input id has exactly one label row.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`. Every locked value below is copied from it. If the two files disagree, the epic step spec wins and this file is wrong.

## Main caller

`data_platform/generate_features/engines/base.py` `BaseBatchExecutionEngine.label_records`, which `generate_features.py` `_run_feature_labeling` calls once per feature. The CLI that reaches it in legacy mode is:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000
```

That command labels 200,000 posts and is not run in this PR. The live checks in this file use the temporary smoke helper with three and five posts.

Happy path through the caller for one chunk: filter already labeled ids, call `label_chunk`, which submits one provider job, writes the state file, polls, parses the output and error files, writes successful rows through the `write_rows` callback, retries failed transient ids in a new provider job, records final failures, and clears the state file. `label_records` then appends the final failures to `deadletter.jsonl`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md` | Locked contracts, smoke commands, forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | `active_openai_batch.json` fields shared with Step 5 |
| `data_platform/generate_features/engines/openai_engine.py` | Current submit and wait flow, output parsing, poll retry |
| `data_platform/generate_features/engines/base.py` | Current whole chunk retry and deadletter loop |
| `data_platform/generate_features/generate_features.py` | Current completion rule based on `failed_batches` |
| `data_platform/generate_features/llm_retry.py` | Existing retry decorator kept for the LangChain and thread pool engines |
| `data_platform/generate_features/deadletter.py` | `append_deadletter_batch` record shape |
| `data_platform/generate_features/models.py` | `FeatureRunConfig.max_label_retries` is 3, so four attempts in total |
| `data_platform/generate_features/metadata.py` | `flush_metadata` atomic write pattern to copy for the state file |
| `data_platform/utils/feature_labels.py` | `filter_unlabeled` used by the completion check |
| `data_platform/utils/storage.py` | `append_records`, `load_records`, `load_seen_ids_from_disk` |
| `tests/data_platform/generate_features/test_openai_engine.py` | Existing contract for `batch_label_records` and `wait_for_completed_batch` that must keep passing |
| `tests/data_platform/generate_features/test_generate_features.py` | Existing completion contract that must keep passing |

## Files allowed to change

- `data_platform/generate_features/openai_batch_state.py` (new)
- `data_platform/generate_features/engines/openai_engine.py`
- `data_platform/generate_features/engines/base.py` (the `label_chunk` hook, failure record, and deadletter grouping only)
- `data_platform/generate_features/generate_features.py` (completion rule only)
- `data_platform/generate_features/smoke_resume_openai_batch.py` (new, temporary, deleted before merge)
- `data_platform/generate_features/RESUME_SMOKE_EVIDENCE.md` (new, temporary, deleted before merge)

`CHANGELOG.md` is edited only in a separate commit after implementation. `models.py` and `metadata.py` are allowed by the epic spec but not needed, because `max_label_retries=3` already gives four attempts and the state file carries the provider job identity.

## Files forbidden to change

- `tests/**`
- `data_platform/generate_features/llm_retry.py`
- `data_platform/generate_features/engines/langchain_engine.py` and `thread_pool_engine.py`
- `data_platform/generate_features/registry.py`, `platform_cli.py`, `generate_bluesky_features.py`, `smoke_openai_engine.py`
- Feature prompt modules under `data_platform/generate_features/is_*`, `political_stance`, `llm_toxicity_tiered`
- `data_platform/utils/**`, `lib/**`, `webapp/**`, `experiments/**`
- Any file under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/` or any earlier child plan folder
- Any S3 write or delete, any git history rewrite

Stage files by explicit path only. Never run `git add -A` or `git add .`. `git status` lists 24 pulled dump parquet files as modified even though `git diff` is empty; never stage them.

## Locked values

| Item | Value |
|------|-------|
| State file path | `{run_dir}/{feature_name}.active_openai_batch.json`, written with a temp file and `os.replace` |
| State fields | `input_file_id`, `batch_id`, `logical_batch_index`, `pending_source_record_ids`, `attempt_count`, `state`, `campaign_id`, `feature_name`, `submitted_at` |
| `state` values | `polling`, `writing`, `terminal` |
| `campaign_id` in legacy mode | `null` |
| `submitted_at` | `lib.timestamp_utils.get_current_timestamp()` |
| Write order | State is on disk before the first `batches.retrieve` for that job |
| Resume rule | A state file matches when `feature_name` equals the current feature, `state` is `polling` or `writing`, and at least one of its `pending_source_record_ids` is in the current chunk. `logical_batch_index` is recorded but not compared, because a new process rebuilds chunks from the ids that are still unlabeled and the same job can land under a different index. A match polls that `batch_id` and never calls `files.create` or `batches.create` for it. Pending ids outside the current chunk are left for the chunk that holds them |
| `terminal` state | Written after the rows and failures of a job are recorded. A `terminal` state never matches on resume |
| Clear rule | The state file is deleted only after every id in the chunk has a written row or a final failure |
| Custom id mapping | `task-{index:05d}` where `index` is the position in `pending_source_record_ids` |
| Transient request failures | `APIConnectionError`, `InternalServerError`, `RateLimitError`, error file lines with HTTP 429 or 5xx, a provider batch that ends `failed`, `expired`, or `cancelled`, and a request missing from both files |
| Non transient request failures | Every other exception and error line, including HTTP 400, 401, 403, 404, structured output missing, and row validation errors |
| Attempt budget | `run_config.max_label_retries + 1` attempts per record, which is 4 with the default of 3 |
| Retry job rule | One provider job at a time per feature run. A retry job holds only the ids that failed transiently and still have budget |
| Deadletter | One `append_deadletter_batch` line per distinct `(error, attempts)` pair in a chunk, `attempts` equal to that record's attempt count |
| Completion rule | `filter_records_needing_features` returns zero rows and the feature file has no duplicate `feature_file_id_column` value. `failed_batches` is still counted but never blocks completion or the run's `sync_status` |
| Legacy `batch_label_records` | Still submits one job without a state file, and still raises `RuntimeError` for error file lines and `ValueError` for ids missing from the output |

## Contracts

`data_platform/generate_features/openai_batch_state.py`:

- `ACTIVE_BATCH_STATE_SUFFIX = ".active_openai_batch.json"`
- `ACTIVE_BATCH_STATES = ("polling", "writing", "terminal")`
- `active_batch_state_path(run_dir: Path, feature_name: str) -> Path`
- `write_active_batch_state(run_dir: Path, feature_name: str, state: dict[str, Any]) -> Path` raises `ValueError` when a required field is missing or `state` is not one of the three values. Atomic replace.
- `load_active_batch_state(run_dir: Path, feature_name: str) -> dict[str, Any] | None` returns `None` when the file is missing.
- `clear_active_batch_state(run_dir: Path, feature_name: str) -> None` is a no-op when the file is missing.

`data_platform/generate_features/engines/base.py`:

- `@dataclass(frozen=True) class RecordLabelFailure: source_record_id: str; error: str; attempts: int`
- `BaseBatchExecutionEngine.label_chunk(self, tasks, *, feature_name, run_dir, batch_index, write_rows: Callable[[list[dict]], None]) -> list[RecordLabelFailure]`. Default body wraps `batch_label_records` in `retry_llm_completion` as today, calls `write_rows` once on success, and returns one failure per task with `attempts = max_label_retries + 1` when every attempt raised.
- `label_records` calls `label_chunk` per chunk, groups the returned failures by `(error, attempts)`, appends one deadletter line per group, adds 1 to `stats.failed_batches` when the list is not empty, and calls `on_batch_complete(rows_written_in_chunk, 1 or 0)` once per chunk.

`data_platform/generate_features/engines/openai_engine.py`:

- `TRANSIENT_HTTP_STATUS_CODES` covers 429 and 500 through 599.
- `class OpenAIBatchJobError(RuntimeError)` raised by `wait_for_completed_batch` for `failed`, `expired`, or `cancelled`.
- `@dataclass(frozen=True) class BatchRequestFailure: source_record_id: str; custom_id: str; error: str; transient: bool; missing_output: bool`
- `@dataclass(frozen=True) class ParsedBatchOutput: rows: list[dict]; failures: list[BatchRequestFailure]`
- `submit_active_batch(client, spec, engine_config, tasks, *, run_dir, feature_name, batch_index, attempt_count) -> dict[str, Any]` uploads, creates the provider batch, writes the `polling` state, and returns the state dict.
- `_parse_completed_batch(client, batch, ordered_ids, tasks_by_id, spec, sleep_fn) -> ParsedBatchOutput` downloads the output file and the error file separately and classifies every id in `ordered_ids` that is a key of `tasks_by_id`. It stays module private because only the engine calls it.
- `OpenAIBatchEngine.label_chunk` overrides the base hook with the resumable loop.
- `OpenAIBatchEngine.batch_label_records` keeps its signature and strict behavior.

`data_platform/generate_features/generate_features.py`:

- `_all_records_labeled_once(records, feature_name, config, feature_storage) -> bool`
- `_run_feature_labeling` takes `records` in addition to `tasks` and marks the feature complete only when `_all_records_labeled_once` is true.
- `_mark_sync_completed` requires every feature `status == "completed"` and no longer requires `failed_batches == 0`.

## Scenarios (given, when, then)

No pytest is added. These scenarios are the behavior the live smoke and the offline check prove.

1. Given a fresh run dir and three tasks, when `label_chunk` runs, then `files.create` and `batches.create` are called once each, the state file exists with `state=polling` before the first `batches.retrieve`, and after the job it is deleted.
2. Given a `polling` state file for chunk 0 with five ids and a provider batch that is still running, when a new process calls `label_chunk` with those five tasks, then `batches.create` is called zero times, `batches.retrieve` is polled for the state's `batch_id`, and five rows are written.
3. Given a provider batch whose output file has two good lines and whose error file has one HTTP 404 line, when `label_chunk` runs, then two rows are written, one `RecordLabelFailure` with `attempts=1` is returned, and no retry job is created.
4. Given an error file line with HTTP 429 for one id, when `label_chunk` runs, then the two good rows are written first and one retry provider job with exactly one request is created.
5. Given a record that fails transiently four times, when `label_chunk` runs, then the record is returned as a failure with `attempts=4` and no fifth job is created.
6. Given `batch_label_records` with an error file line, when it runs, then it raises `RuntimeError` naming the custom id, as today.
7. Given every input record has a row and no id repeats, when `_run_feature_labeling` finishes, then the feature is `completed` even if `failed_batches` is greater than zero.
8. Given one input record has no row, when `_run_feature_labeling` finishes, then the feature stays `in_progress`.

## Ordered implementation work

1. Scaffold `openai_batch_state.py` with stub bodies, the `label_chunk` hook stub on the base engine, the new dataclasses, and the smoke helper module with a Typer skeleton. Commit.
2. Fill in the signatures above. Commit.
3. Record the scenarios above in this file. Commit.
4. Implement `openai_batch_state.py`. Run the offline wiring check. Commit.
5. Implement `_parse_completed_batch` and the failure classification. Make `batch_label_records` use it and keep its strict raises. Commit.
6. Implement `submit_active_batch` and `OpenAIBatchJobError`. Commit.
7. Implement `OpenAIBatchEngine.label_chunk`. Commit.
8. Implement the default `label_chunk` and the new `label_records` loop in `base.py`. Commit.
9. Implement the completion rule in `generate_features.py`. Commit.
10. Implement `smoke_resume_openai_batch.py`. Run the two live smokes. Commit the helper and `RESUME_SMOKE_EVIDENCE.md`. Commit.
11. Run `uv run pytest -q`. Expect 631 passed.
12. Delete the two temporary files in a final commit before merge.

## Exact commands with expected output

### Offline wiring check (no OpenAI call)

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
from data_platform.generate_features import openai_batch_state as s
from pathlib import Path
import tempfile
d = Path(tempfile.mkdtemp())
state = {
    'campaign_id': 'bluesky_2026_09_03_235130_llm_features_v1',
    'feature_name': 'is_news_or_opinion',
    'input_file_id': 'file-test',
    'batch_id': 'batch_test',
    'logical_batch_index': 0,
    'pending_source_record_ids': ['at://example/1'],
    'attempt_count': 1,
    'state': 'polling',
    'submitted_at': '2026-09-05T18:30:00Z',
}
s.write_active_batch_state(d, 'is_news_or_opinion', state)
loaded = s.load_active_batch_state(d, 'is_news_or_opinion')
assert loaded['batch_id'] == 'batch_test'
print('openai_batch_state wiring OK')
"
```

Expected stdout:

```text
openai_batch_state wiring OK
```

### Live partial-success check (requires `OPENAI_API_KEY`)

```bash
cd /workspace

PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode partial-success \
  --feature is_news_or_opinion \
  --post-count 3
```

Expected stdout includes both lines:

```text
partial_success_rows=2
partial_failure_rows=1
```

The smoke forces the failure by rewriting the third request's `temperature` to 5.0 before the upload. The provider answers that request with an HTTP 400 error line, which is non transient, so no retry job is created. A bad model name does not work here because OpenAI then fails the whole batch at file validation.

### Live interrupt-and-resume check (requires `OPENAI_API_KEY`)

```bash
cd /workspace

PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode interrupt \
  --feature is_news_or_opinion \
  --post-count 5 \
  --stop-after-submit

# In a second shell, resume the same run directory printed by the command above:
PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode resume \
  --feature is_news_or_opinion \
  --run-dir /tmp/<printed-run-dir>
```

Expected stdout on resume:

```text
reattached_batch_id=batch_...
completed_without_resubmit=true
labeled_count=5
```

### Existing suite

```bash
cd /workspace
uv run pytest -q
```

Expected: `631 passed`.

## Must pass

- The offline wiring check prints `openai_batch_state wiring OK`.
- The partial-success smoke prints `partial_success_rows=2` and `partial_failure_rows=1`.
- The resume smoke prints `completed_without_resubmit=true` and `labeled_count=5`, and the `reattached_batch_id` equals the `batch_id` printed by the interrupt command.
- `uv run pytest -q` reports 631 passed with no test file changes.

## Must fail

- Any code path that creates a second provider batch for ids covered by a `polling` or `writing` state file.
- Any code path that drops successful rows because another row in the same provider batch failed.
- Any retry of an HTTP 400, 401, 403, or 404 error line.
- Any feature marked `completed` while an input record has no label row.
