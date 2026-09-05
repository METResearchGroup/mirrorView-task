# Step 4: Harden OpenAI Batch feature generation and resume

## Goal

Make OpenAI Batch labeling resumable across process crashes without creating duplicate provider jobs or duplicate charges. Persist `input_file_id` and `batch_id` before polling begins, reattach to the same in-flight batch after interruption, keep successful rows from partly failed batches, retry only transient failures up to four attempts per record, and mark a feature complete only when every pinned input id has exactly one valid output row.

## Real dependencies

Steps 1 through 3 from `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` must be merged first. Production reads and writes must go through the S3-backed pipeline storage added in Step 2 and defaulted in Step 3. This step does not add S3 shard layout or Parquet shard writers; Step 5 owns durable shard files. This step only hardens the OpenAI Batch engine and the orchestrator hooks it needs for crash-safe provider job identity.

Pinned campaign inputs used in smoke and later steps:

- Campaign id: `bluesky_2026_09_03_235130_llm_features_v1`
- Dataset id: `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`
- Preprocessed run: `2026_09_03-23:51:30`
- Expected unique input ids: `200000`

## Main caller and one implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000 \
  --checkpoint <FEATURE_RUN_TIMESTAMP>
```

**One implementation slice for this PR:** split `_submit_and_wait_for_batch` in `data_platform/generate_features/engines/openai_engine.py` into explicit submit, durable state write, poll-or-resume, and partial-result parse paths. Add one small state module that atomically writes and reloads `{input_file_id, batch_id, task_uris, feature_name, campaign_id}` before the first poll call.

**Out of scope for this PR:** immutable 2000-row S3 Parquet shards, `manifest.json`, `progress.jsonl`, ten-post smoke cost reports, campaign approval gate, watcher comments, lifecycle tagging, and any change to feature prompt text or registry membership.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Parent plan Step 4 scope |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Current submit-and-wait flow; no persisted provider ids |
| `/workspace/data_platform/generate_features/engines/base.py` | Blocking batch loop, deadletter on whole-batch failure |
| `/workspace/data_platform/generate_features/generate_features.py` | Feature completion gate and metadata flush |
| `/workspace/data_platform/generate_features/metadata.py` | Run metadata shape |
| `/workspace/data_platform/generate_features/models.py` | `FeatureRunConfig.max_label_retries` default |
| `/workspace/data_platform/generate_features/llm_retry.py` | Current retry decorator retries all exceptions |
| `/workspace/data_platform/generate_features/deadletter.py` | Deadletter record shape |
| `/workspace/data_platform/generate_features/platform_cli.py` | Checkpoint resume entry |
| `/workspace/data_platform/generate_features/registry.py` | Seven OpenAI LLM features |
| `/workspace/data_platform/utils/storage.py` | Append and resume reads after Step 3 S3 backend |
| `/workspace/lib/load_env_vars.py` | `OPENAI_API_KEY` loading |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL` (`gpt-5.4-nano`) |

## Files allowed to change

- `/workspace/data_platform/generate_features/engines/openai_engine.py`
- `/workspace/data_platform/generate_features/engines/base.py` (only hooks needed for partial batch success and per-record retry accounting)
- `/workspace/data_platform/generate_features/openai_batch_state.py` (new)
- `/workspace/data_platform/generate_features/generate_features.py` (completion rule: complete when every pinned id has a label, not when `failed_batches > 0` from an earlier transient streak)
- `/workspace/data_platform/generate_features/metadata.py` (optional fields for active provider job identity; do not break existing local metadata readers)
- `/workspace/data_platform/generate_features/models.py` (raise default `max_label_retries` to `4` for campaign runs only if needed; keep backward-compatible default for non-campaign CLI use)
- `/workspace/data_platform/generate_features/smoke_resume_openai_batch.py` (new temporary smoke helper for this PR; see commands below)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md`
- `/workspace/tests/**` (do not add, edit, or run automated tests)
- `/workspace/data_platform/generate_features/is_*/*.py` feature prompt modules
- `/workspace/data_platform/generate_features/political_stance/generate_feature.py`
- `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py`
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents or other autonomous agent runners

## Locked contracts

### Blocking engine and one active OpenAI Batch job

Keep the blocking engine model. For one feature run at a time, at most one OpenAI Batch job may be in flight. Do not submit a second batch for the same feature until the current batch reaches a terminal provider status or is explicitly abandoned in deadletter after four failed attempts per remaining record.

### Provider identity persistence

Before the first `batches.retrieve` poll call, atomically persist a JSON state file next to the active feature run with at least:

```json
{
  "campaign_id": "bluesky_2026_09_03_235130_llm_features_v1",
  "feature_name": "is_news_or_opinion",
  "input_file_id": "file-...",
  "batch_id": "batch_...",
  "task_uris": ["at://...", "..."],
  "submitted_at": "2026-09-05T18:30:00Z",
  "status": "polling"
}
```

On resume, if this state file exists and provider status is non-terminal, reload it and continue polling the same `batch_id`. Never call `files.create` or `batches.create` again for that in-flight job.

Clear the state file only after all successful rows from that batch are durably written and every still-missing id in the batch has either succeeded on retry or landed in deadletter with four attempts recorded.

### Partial batch success

Replace whole-batch failure when OpenAI returns mixed success and error lines. Parse output and error files separately. Write every successful structured row immediately. Retry only the failed custom ids, up to four attempts per record, using the same blocking one-batch-at-a-time rule for each retry batch.

Do not discard successful rows because another row in the same provider batch failed.

### Transient failure policy

Retry only transient provider and transport failures: `APIConnectionError`, `InternalServerError`, `RateLimitError`, HTTP 429, and HTTP 5xx. Non-transient schema, auth, and validation failures go straight to deadletter for that record after one non-retryable failure.

Per-record attempt budget: four attempts total, including the first try.

### Exact input id completeness

Completion for a feature requires exactly one valid output row per pinned input id from the campaign input set. Duplicate outputs for the same `source_record_id` are forbidden. Missing ids keep the feature `in_progress`.

### Retry count alignment

Campaign runs use `max_label_retries=4`, which means four attempts per record under the locked contract above. Do not introduce a second retry counter with a different meaning.

## Ordered implementation work

1. Add `openai_batch_state.py` with atomic write, load, and clear helpers keyed by feature run directory and feature name.
2. Refactor `openai_engine.py` so submit persists `input_file_id` and `batch_id` before polling, and poll uses `wait_for_completed_batch(batch_id)` on resume instead of creating a new batch.
3. Change output parsing so successful lines become rows even when the error file is non-empty; collect failed custom ids for targeted retry batches instead of raising on the first error line.
4. Restrict `retry_llm_completion` for OpenAI Batch paths to transient exception types only, or add an OpenAI-specific retry wrapper used by the engine.
5. Update `generate_features.py` completion logic so a feature can finish when every pinned id is labeled, even if earlier batches logged transient failures that later retries cleared.
6. Add `smoke_resume_openai_batch.py` that submits a tiny live batch, writes state, sleeps, exits, and documents the exact resume command.
7. Run the live smoke commands in this spec. Commit temporary smoke evidence. Delete temporary smoke helper and evidence before merge.

## Exact live smoke/basic check commands with expected output

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
    'task_uris': ['at://example/1'],
    'submitted_at': '2026-09-05T18:30:00Z',
    'status': 'polling',
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

Use the temporary helper added in this PR with exactly three posts, one intentionally empty-text post that will fail validation, and two valid posts:

```bash
cd /workspace

PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode partial-success \
  --feature is_news_or_opinion \
  --post-count 3
```

Expected stdout includes both of the following lines:

```text
partial_success_rows=2
partial_failure_rows=1
```

Expected filesystem effect: two valid label rows are written; one failed id is queued for retry rather than losing the successful rows.

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

Expected provider behavior: exactly one `batches.create` call for the interrupted job across both commands.

## Acceptance criteria

- A crash after submit and before poll resumes the same `batch_id` without a second `batches.create` for that job.
- Mixed success and failure within one provider batch keeps successful rows and retries only failed ids.
- Each record gets at most four attempts for transient failures.
- A feature is marked complete only when all pinned input ids have exactly one valid output row.
- Blocking semantics remain: one active OpenAI Batch job per feature run at a time.
- Temporary smoke helper and smoke evidence are committed for review during the PR and removed before merge.
- No automated tests were added or run.

## Failure conditions

- A resume path creates a second OpenAI Batch job for the same in-flight work.
- A partly successful provider batch throws away successful rows.
- Non-transient failures retry four times instead of failing fast.
- Feature completion depends on stale `failed_batches` counters while unlabeled ids still exist.
- Any edit under `/workspace/tests/**`.
- Any code path that launches Cursor agents or other autonomous agent runners.
- Changes to feature prompts, registry membership, S3 shard layout, smoke cost gate, or watcher comments.

## PR artifact/commit rules

- Branch name: `cursor/harden-openai-batch-resume-86b0`
- One focused commit series inside the PR; prefer separate commits for engine refactor, orchestrator completion rule, and temporary smoke helper.
- Commit the temporary smoke helper and a short `RESUME_SMOKE_EVIDENCE.md` under `data_platform/generate_features/` during review.
- Before merge, delete `smoke_resume_openai_batch.py` and `RESUME_SMOKE_EVIDENCE.md`, and squash or add a final cleanup commit that removes them.
- PR title: `Harden OpenAI Batch feature generation and resume`
- PR body must state: no pytest added, live smoke commands run, and temporary smoke files removed before merge.
