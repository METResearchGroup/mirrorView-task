# OpenAI Batch resume smoke evidence

Temporary review artifact for issue #184. Delete before merge. All runs used
`gpt-5.4-nano` through the live OpenAI Batch API on 2026-09-06 with tiny inputs
(3 and 5 posts). Nothing was written to S3.

## Offline wiring check

Command: the `openai_batch_state` snippet from `steps/step4.md`.

```text
openai_batch_state wiring OK
```

## Live partial-success check (3 posts, one request broken with `temperature=5.0`)

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode partial-success --feature is_news_or_opinion --post-count 3
```

```text
run_dir=/tmp/smoke_partial_lc8dl3pv
partial_success_rows=2
partial_failure_rows=1
partial_failure={"source_record_id": "at://smoke/post/2", "error": "HTTP 400: Invalid 'temperature': decimal above maximum value. Expected a value <= 2, but got 5 instead.", "attempts": 1}
provider_calls={"files.create": 1, "batches.create": 1, "batches.retrieve": 4}
active_state_after=cleared
```

The two good rows were written, the HTTP 400 line was classified non transient
and recorded after one attempt, no retry job was created, and the state file
was cleared.

## Live interrupt-and-resume check (5 posts)

First process, exits right after the state file is written:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode interrupt --feature is_news_or_opinion --post-count 5 --stop-after-submit
```

```text
run_dir=/tmp/smoke_resume_h2f4tpjj
state_path=/tmp/smoke_resume_h2f4tpjj/is_news_or_opinion.active_openai_batch.json
batch_id=batch_6a9ccc69c38c8190b479ffd628689e9e
input_file_id=file-MBP2FEJLuC3v73u9m9RLSm
state=polling
provider_calls={"files.create": 1, "batches.create": 1, "batches.retrieve": 0}
```

State file on disk at exit (before any `batches.retrieve` call):

```json
{
  "input_file_id": "file-MBP2FEJLuC3v73u9m9RLSm",
  "batch_id": "batch_6a9ccc69c38c8190b479ffd628689e9e",
  "logical_batch_index": 0,
  "pending_source_record_ids": [
    "at://smoke/post/0",
    "at://smoke/post/1",
    "at://smoke/post/2",
    "at://smoke/post/3",
    "at://smoke/post/4"
  ],
  "attempt_count": 1,
  "state": "polling",
  "campaign_id": null,
  "feature_name": "is_news_or_opinion",
  "submitted_at": "2026_09_06-02:14:01"
}
```

Second process, same run directory:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \
  --mode resume --feature is_news_or_opinion --run-dir /tmp/smoke_resume_h2f4tpjj
```

```text
reattached_batch_id=batch_6a9ccc69c38c8190b479ffd628689e9e
completed_without_resubmit=true
labeled_count=5
failure_count=0
provider_calls={"files.create": 0, "batches.create": 0, "batches.retrieve": 5}
active_state_after=cleared
```

The second process polled the same `batch_id` from the state file, made zero
`files.create` and zero `batches.create` calls, wrote all five rows, and
cleared the state file.

## Earlier live run that changed the design

The first partial-success attempt broke one request by giving it a model name
that does not exist. OpenAI rejected the whole batch at file validation with
status `failed` and error code `model_not_found`, and the engine at that point
treated every terminal failure as transient, so it resubmitted the same batch
four times (four free failed batches, no charges). The engine now treats a
`failed` batch as transient only when every error code is
`token_limit_exceeded`, treats `cancelled` as non transient, and parses an
`expired` batch for the rows that did finish. The smoke now breaks one request
with an out of range temperature, which produces the per request HTTP 400
line shown above.
