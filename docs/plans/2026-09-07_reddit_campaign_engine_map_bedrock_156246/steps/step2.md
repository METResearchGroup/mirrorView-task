# Step 2: Generalize Bedrock Converse and add the Bedrock S3 campaign writer

## Scope

- **Caller:** `generate_campaign_feature` when `campaign_engine_type` returns `bedrock`, used by `generate_reddit_features` for `is_likely_spam`, `is_self_contained`, and `is_structurally_complete`.
- **Task:** Build Bedrock JSON instructions from each `FeatureSpec` schema. Treat content filter as a typed failure. Label one 2,000 row part at a time with eight threads. Persist `active_bedrock_job.json`. Record content filter errors, then retry those ids through OpenAI Batch in the same command. Keep OpenAI campaign labeling for map entries with `openai`.
- **Out of scope:** Full 400,000 row production, Reddit smoke module, watcher platform flags, registry engine defaults, pytest, GitHub posting.

Phase 4 for this package is the offline and optional live smoke in Step 3, not pytest. Do not add files under `tests/`. Run unattended. Skip Phase 3 approval.

## Files to inspect

- `data_platform/generate_features/engines/bedrock_engine.py`
- `data_platform/generate_features/generate_features.py`
- `data_platform/generate_features/s3_feature_campaign.py`
- `data_platform/generate_features/s3_feature_batches.py`
- `data_platform/generate_features/engines/openai_engine.py`
- `data_platform/generate_features/engines/base.py`
- `lib/constants.py`

## Files allowed to change

- `data_platform/generate_features/engines/bedrock_engine.py`
- `data_platform/generate_features/engines/bedrock_campaign.py` (new)
- `data_platform/generate_features/generate_features.py`
- `data_platform/generate_features/s3_feature_campaign.py`
- `data_platform/generate_features/s3_feature_batches.py` (only if a helper is required for error reason or Bedrock batch write)

## Files forbidden to change

- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/models.py`
- `data_platform/utils/storage.py`
- Feature prompt modules
- Any file under `tests/`
- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/**`
- Step 3 smoke modules, including any new `smoke_reddit_campaign.py`

## Locked contracts

### Bedrock Converse

Replace the hardcoded news or opinion JSON instruction with a JSON instruction derived from `spec.llm_output_schema`. Keep the feature `system_prompt` from the spec.

Content filter is a failure. Raise a dedicated error type, for example `BedrockContentFilterError`, when the provider text contains `blocked by our content filters` or the Converse stop reason is a content filter. Do not map content filter to `neither`, `false`, or any other label. Do not retry content filter on Bedrock. Other invalid JSON may still retry inside Converse.

### Bedrock campaign writer

Reuse `write_batch`, `adopt_unrecorded_batch`, `consolidate_final`, and `append_errors`. Do not overwrite an existing `part-NNNNN.parquet`.

Bedrock concurrency inside a part is 8. Force that value in the Bedrock campaign writer. Never start extra Bedrock processes from this code.

`active_bedrock_job.json` minimum fields:

| Field | Meaning |
| ----- | ------- |
| `logical_batch_index` | Zero based part index in progress |
| `pending_source_record_ids` | Ordered ids still expected for this part |
| `completed_source_record_ids` | Ids already labeled for this part |
| `state` | `running`, `writing`, or `terminal` |

Use the same conditional replace pattern as `active_openai_batch.json`. Delete the Bedrock job file only after the part object exists and the manifest records it. Never store Bedrock cursor state in `active_openai_batch.json`.

Row metadata stays the six `LabelRowMetadataModel` fields plus the feature label field. `batch_id` is the Bedrock job id for Bedrock rows and the OpenAI batch id for retry rows. No parquet `engine_type` column.

Tag `batches/` uploads with `intermediate-artifact=true`. Do not tag `final.parquet`, `manifest.json`, `progress.jsonl`, or `errors.jsonl`.

### Content filter retry

When Bedrock blocks a comment, append:

```json
{
  "source_record_id": "<id>",
  "reason": "bedrock_content_filter",
  "engine_type": "bedrock",
  "detail": "<provider message excerpt>",
  "recorded_at": "<UTC timestamp>"
}
```

The same command then submits those ids to OpenAI Batch using the existing OpenAI chunk writer and `active_openai_batch.json`. Successful retries write additional immutable batch objects. Other Bedrock failures stay failed and are not retried. After retries, the manifest keeps `engine_type` equal to `bedrock` and adds:

```json
"openai_content_filter_retry": {
  "count": 0,
  "model_id": "gpt-5.4-nano",
  "provider_batch_ids": []
}
```

`count` is the number of ids submitted to OpenAI retry. `model_id` is `lib.constants.DEFAULT_LLM_MODEL`. `provider_batch_ids` lists OpenAI batch ids from successful retry writes.

On resume, retry content filter ids that still have no batch row.

Do not write under the pinned campaign prefix during this step. Optional live proof uses only `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/`.

Keep functions under 20 lines. Named constants. Numpy docstrings.

## Ordered units of work

1. JSON instruction from schema and content filter error type in `bedrock_engine.py`.
2. Per task Bedrock labeling that returns successes, content filter failures, and other failures.
3. `active_bedrock_job.json` load, save, and delete helpers.
4. Serial Bedrock part labeling with resume and immutable batch write.
5. Content filter error records and OpenAI retry that updates `openai_content_filter_retry`.
6. `generate_campaign_feature` routes Bedrock map entries to the new writer.

## Must pass

Offline import of the Bedrock campaign module and confirmation that content filter parsing no longer returns `neither`:

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.engines.bedrock_engine import (
    BedrockContentFilterError,
    parse_json_object,
)
try:
    parse_json_object('blocked by our content filters')
except BedrockContentFilterError:
    print('content_filter_is_failure OK')
else:
    raise SystemExit('content filter must not parse as a label')
"
```

Expected stdout: `content_filter_is_failure OK`

## Must fail

- Hardcoded news or opinion JSON for every Bedrock feature.
- Content filter stored as `neither` or boolean false.
- Shared resume file for Bedrock and OpenAI.
- Overwriting an existing batch object.
- Writes under the pinned campaign `batches/` prefix.
- An `engine_type` parquet column.
- More than one Bedrock process started by this writer.
- Any file under `tests/`.
