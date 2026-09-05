# Step 4: Harden OpenAI Batch feature generation and resume

## Goal

Make OpenAI Batch labeling resumable across process crashes without creating duplicate provider jobs or duplicate charges. Persist `input_file_id` and `batch_id` before polling begins. Reattach to the same in-flight batch after interruption and keep successful rows from partly failed batches. Retry only transient failures up to four attempts per record. Mark a feature complete only when every pinned input id has exactly one valid output row.

## Dependencies

- **None.** This step may run in parallel with Steps 1 and 2.
- See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for pinned campaign constants and the `active_openai_batch.json` state contract.

This step hardens the OpenAI Batch engine only. It defines provider state independent of storage backend. Step 5 persists campaign state in S3. This step does not add campaign S3 layout, smoke tooling, or watcher comments.

Pinned campaign inputs used in smoke and later steps:

- Campaign id: `bluesky_2026_09_03_235130_llm_features_v1`
- Dataset id: `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`
- Preprocessed run: `2026_09_03-23:51:30`
- Expected unique input ids: `200000`

## Main caller and implementation slice

**Main caller after this PR merges (legacy mode smoke; campaign flags arrive in Step 5):**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000
```

**One implementation slice for this PR:** split `_submit_and_wait_for_batch` in `data_platform/generate_features/engines/openai_engine.py` into explicit submit, durable state write, poll-or-resume, and partial-result parse paths. Add one small state module that defines the `active_openai_batch.json` contract and writes or reloads state before the first poll call. Storage backend is pluggable; Step 5 maps this contract to S3.

**Out of scope for this PR:** campaign S3 prefix layout, `manifest.json`, `progress.jsonl`, Q44 provenance columns on rows, ten-post smoke cost reports, watcher comments, lifecycle tagging, `--campaign-id`, `--preprocessed-run`, and any change to feature prompt text or registry membership.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Locked campaign constants |
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Parent plan Step 4 scope |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Current submit-and-wait flow |
| `/workspace/data_platform/generate_features/engines/base.py` | Blocking batch loop |
| `/workspace/data_platform/generate_features/generate_features.py` | Feature completion gate |
| `/workspace/data_platform/generate_features/metadata.py` | Run metadata shape |
| `/workspace/data_platform/generate_features/models.py` | `FeatureRunConfig.max_label_retries` |
| `/workspace/data_platform/generate_features/llm_retry.py` | Current retry decorator |
| `/workspace/data_platform/generate_features/deadletter.py` | Deadletter record shape |
| `/workspace/data_platform/generate_features/platform_cli.py` | CLI entry |
| `/workspace/data_platform/generate_features/registry.py` | Seven OpenAI LLM features |
| `/workspace/data_platform/utils/storage.py` | Append and resume reads |
| `/workspace/lib/load_env_vars.py` | `OPENAI_API_KEY` loading |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL` (`gpt-5.4-nano`) |

## Files allowed to change

- `/workspace/data_platform/generate_features/engines/openai_engine.py`
- `/workspace/data_platform/generate_features/engines/base.py` (only hooks needed for partial batch success and per-record retry accounting)
- `/workspace/data_platform/generate_features/openai_batch_state.py` (new)
- `/workspace/data_platform/generate_features/generate_features.py` (completion rule: complete when every pinned id has a label)
- `/workspace/data_platform/generate_features/metadata.py` (optional fields for active provider job identity)
- `/workspace/data_platform/generate_features/models.py` (raise default `max_label_retries` to `4` for campaign runs if needed)
- `/workspace/data_platform/generate_features/smoke_resume_openai_batch.py` (new temporary smoke helper)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md` through `step7.md`
- `/workspace/tests/**`
- Feature prompt modules under `/workspace/data_platform/generate_features/is_*`, `political_stance`, and `llm_toxicity_tiered`
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents or other autonomous agent runners

## Locked contracts

See `campaign_contract.md`. This step owns engine behavior only.

### Blocking engine and one active OpenAI Batch job

Keep the blocking engine model. For one feature run at a time, at most one OpenAI Batch job may be in flight. Do not submit a second batch for the same feature until the current batch reaches a terminal provider status or is explicitly abandoned in deadletter after four failed attempts per remaining record.

### `active_openai_batch.json` state contract (storage agnostic)

Before the first `batches.retrieve` poll call, persist state with at least:

| Field | Meaning |
|-------|---------|
| `input_file_id` | OpenAI files id for the submitted batch input |
| `batch_id` | OpenAI Batch provider id |
| `logical_batch_index` | Zero-based canonical part index this job will populate |
| `pending_source_record_ids` | Ordered ids still expected from this provider job |
| `attempt_count` | Per-job attempt counter |
| `state` | `polling`, `writing`, or `terminal` |
| `campaign_id` | `bluesky_2026_09_03_235130_llm_features_v1` when in campaign mode |
| `feature_name` | Feature being labeled |
| `submitted_at` | UTC timestamp |

On resume, if state exists and provider status is non-terminal, reload it and continue polling the same `batch_id`. Never call `files.create` or `batches.create` again for that in-flight job.

Clear state only after all successful rows from that provider job are durably written to an immutable batch object and recorded in `manifest.json`, and every still-missing id has either succeeded on retry or landed in deadletter with four attempts recorded.

Step 5 stores this contract at `{feature}/active_openai_batch.json` in S3 with conditional atomic replace.

### Partial batch success

Replace whole-batch failure when OpenAI returns mixed success and error lines. Parse output and error files separately. Write every successful structured row immediately. Retry only the failed custom ids, up to four attempts per record, using the same blocking one-batch-at-a-time rule for each retry batch.

Do not discard successful rows because another row in the same provider batch failed.

### Transient failure policy

Retry only transient provider and transport failures: `APIConnectionError`, `InternalServerError`, `RateLimitError`, HTTP 429, and HTTP 5xx. Non-transient schema, auth, and validation failures go straight to deadletter for that record after one non-retryable failure.

Per-record attempt budget: four attempts total, including the first try.

### Exact input id completeness

Completion for a feature requires exactly one valid output row per pinned input id from the campaign input set. Duplicate outputs for the same `source_record_id` are forbidden. Missing ids keep the feature `in_progress`.

## Ordered implementation work

1. Add `openai_batch_state.py` with atomic write, load, and clear helpers keyed by feature run directory and feature name.
2. Refactor `openai_engine.py` so submit persists `input_file_id` and `batch_id` before polling, and poll uses `wait_for_completed_batch(batch_id)` on resume instead of creating a new batch.
3. Change output parsing so successful lines become rows even when the error file is non-empty; collect failed custom ids for targeted retry batches instead of raising on the first error line.
4. Restrict `retry_llm_completion` for OpenAI Batch paths to transient exception types only, or add an OpenAI-specific retry wrapper used by the engine.
5. Update `generate_features.py` completion logic so a feature can finish when every pinned id is labeled, even if earlier batches logged transient failures that later retries cleared.
6. Add `smoke_resume_openai_batch.py` that submits a tiny live batch, writes state, sleeps, exits, and documents the exact resume command.
7. Run the live smoke commands in this spec. Commit temporary smoke evidence. Delete temporary smoke helper and evidence before merge.

## Exact live smoke and basic check commands with expected output

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

Expected stdout includes both of the following lines:

```text
partial_success_rows=2
partial_failure_rows=1
```

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
- Changes to feature prompts, registry membership, campaign S3 layout, smoke cost gate, or watcher comments in this PR.

## PR artifact and commit rules

- One focused PR for engine hardening only.
- Commit the temporary smoke helper and a short `RESUME_SMOKE_EVIDENCE.md` under `data_platform/generate_features/` during review.
- Before merge, delete `smoke_resume_openai_batch.py` and `RESUME_SMOKE_EVIDENCE.md`.
- PR title: `Harden OpenAI Batch feature generation and resume`
- PR body must state: no pytest added, live smoke commands run, and temporary smoke files removed before merge.
