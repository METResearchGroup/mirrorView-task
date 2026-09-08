# Step 1: Parameterize Bedrock max tokens and add the shared flip generator

## Scope

- **Caller:** `shared/flip_generation/generate_flips.py` `generate_flips`
- **Task:** Thread `max_tokens` through the existing Bedrock Converse helpers with default `BEDROCK_MAX_TOKENS`. Add `shared/flip_generation/` that takes a posts dataframe, calls `label_tasks_collecting_failures`, and writes one immutable S3 parquet part per batch.
- **Out of scope:** the experiment command, live Bedrock, truncation, June flip scripts, the filter-posts README, `write_batch` in `s3_feature_batches.py`, `FeaturePaths.for_campaign`, changing `build_bedrock_engine`, pytest, new files under `tests/` or `shared/flip_generation/tests/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/plan.md` | Approved contracts, models, S3 layout, loop sketch |
| `/workspace/data_platform/generate_features/engines/bedrock_engine.py` | `converse_label`, `_converse_once`, `label_tasks_collecting_failures`, `_label_task_or_failure`, `_run_label_pool`, `_label_tasks_in_order`, `BEDROCK_MAX_TOKENS`, `create_bedrock_runtime_client` |
| `/workspace/data_platform/generate_features/engines/base.py` | `RecordLabelFailure`, `batched` |
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `LabelTask` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore.put_new`, `list_keys`, `append_jsonl`, `INTERMEDIATE_ARTIFACT_TAG` |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | `rows_to_parquet_bytes`, `parquet_rows` |
| `/workspace/data_platform/generate_features/is_political/generate_feature.py` | Split LLM output model vs persisted row model |
| `/workspace/experiments/scaled_mirrors_generation_2026_06_02/prompts.py` | `FLIP_PROMPT` text to copy, not import |
| `/workspace/experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py` | Topic-alignment sentence |
| `/workspace/lib/constants.py` | `DEFAULT_BEDROCK_SONNET_MODEL`, `BEDROCK_REGION` |

## Files allowed to change

- `/workspace/data_platform/generate_features/engines/bedrock_engine.py` (`max_tokens` parameter only; default remains `BEDROCK_MAX_TOKENS`)
- `/workspace/shared/flip_generation/__init__.py` (new)
- `/workspace/shared/flip_generation/models.py` (new)
- `/workspace/shared/flip_generation/prompts.py` (new)
- `/workspace/shared/flip_generation/s3_parts.py` (new)
- `/workspace/shared/flip_generation/generate_flips.py` (new)

## Files forbidden to change

- `/workspace/tests/**`
- `/workspace/shared/flip_generation/tests/**`
- `/workspace/data_platform/generate_features/engines/bedrock_campaign.py`
- `/workspace/data_platform/generate_features/s3_feature_batches.py` (import `rows_to_parquet_bytes` / `parquet_rows`; do not call `write_batch`)
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/**`
- `/workspace/experiments/truncate_posts_2026_06_19/**`
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/generate_flips_2026_09_08/**` (Step 2)
- `/workspace/CHANGELOG.md` until Step 3 has a live S3 object
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/plan.md`

## File-level constants

Put named constants at module top. Do not put numeric or string literals in function bodies except by referencing those names.

`shared/flip_generation/generate_flips.py`:

- `BATCH_SIZE = 25`
- `MAX_CONCURRENCY = 10`
- `MAX_TOKENS = 2048`
- `FEATURE_NAME = "flip"`
- `RECORD_ID_COLUMN = "record_id"`
- `TEXT_COLUMN = "text"`
- `STANCE_COLUMN = "political_stance"`
- `TOXICITY_COLUMN = "llm_toxicity_tier"`
- `SORT_KIND = "mergesort"`
- `LEFT_STANCE = "left"`
- `RIGHT_STANCE = "right"`
- `REQUIRED_COLUMNS` tuple of the four column names (`record_id`, `text`, `political_stance`, `llm_toxicity_tier`)
- `TARGET_GROUP_BY_STANCE` mapping `left` → `right`, `right` → `left`

`shared/flip_generation/s3_parts.py`:

- `BATCHES_DIRNAME = "batches"`
- `PART_FILENAME_TEMPLATE = "part-{part_index:05d}.parquet"`
- `ERRORS_FILENAME = "errors.jsonl"`
- `FINAL_FILENAME = "flips.parquet"`

`shared/flip_generation/models.py`:

- `FLIP_PARQUET_COLUMNS` tuple in persist order: `record_id`, `original_text`, `llm_toxicity_tier`, `political_stance`, `mirrored_text`, `explanation`, `label_timestamp`

`shared/flip_generation/prompts.py`:

- `TARGET_GROUP_PLACEHOLDER` = the June bracket string
- `USER_TARGET_GROUP_PHRASE = "the target group named in the user message"`
- `TOPIC_ALIGNMENT_INSTRUCTION` = the truncation-v5 sentence
- `USER_MESSAGE_TEMPLATE` for the `LabelTask` user text

The experiment command (Step 2) is the highest-level caller. It passes `BATCH_SIZE`, `MAX_CONCURRENCY`, `MAX_TOKENS`, `DEFAULT_BEDROCK_SONNET_MODEL`, and a Bedrock client into `generate_flips`. `generate_flips` takes those as required arguments and does not default them.

## Bedrock `max_tokens` contract

Thread `max_tokens: int = BEDROCK_MAX_TOKENS` through every function that calls `client.converse` or `converse_label`:

- `converse_label`
- `_converse_once`
- `_label_tasks_in_order`
- `label_tasks_collecting_failures`
- `_run_label_pool`
- `_label_task_or_failure`

`_converse_once` must pass `"maxTokens": max_tokens` in `inferenceConfig`. Temperature stays `BEDROCK_TEMPERATURE`.

`build_bedrock_engine` stays on `DEFAULT_BEDROCK_NOVA_MICRO` and must not pass `max_tokens`, so feature labeling keeps `BEDROCK_MAX_TOKENS`.

Do not add tests under `tests/data_platform/generate_features/`. Existing Bedrock tests must still pass if run; do not edit them.

## Shared models (`shared/flip_generation/models.py`)

`extra="forbid"` on all three Pydantic models. No optional fields.

`FlipLlmOutput`: `flipped_text: str` (`min_length=1`), `explanation: str` (`min_length=1`). This is `FeatureSpec.llm_output_schema`.

`FlipEngineRow`: `source_record_id: str`, `label_timestamp: str`, `flipped_text: str`, `explanation: str`. This is `FeatureSpec.model`.

`FlipRow`: `record_id: str` (`min_length=1`), `original_text: str` (`min_length=1`), `llm_toxicity_tier: str` (`min_length=1`), `political_stance: Literal["left", "right"]`, `mirrored_text: str` (`min_length=1`), `explanation: str` (`min_length=1`), `label_timestamp: str` (`min_length=1`).

`FlipRunResult` frozen dataclass, all fields required: `run_prefix: str`, `part_count: int`, `row_count: int`, `failed_count: int`, `final_key: str`, `wrote_final: bool`. `final_key` is always `final_key(run_prefix)`. `wrote_final` is true only after `flips.parquet` exists.

## Prompt and FeatureSpec

Copy `FLIP_PROMPT` from `/workspace/experiments/scaled_mirrors_generation_2026_06_02/prompts.py` into `shared/flip_generation/prompts.py`. Do not import from `experiments/`.

Replace `TARGET_GROUP_PLACEHOLDER` with `USER_TARGET_GROUP_PHRASE`. Append `TOPIC_ALIGNMENT_INSTRUCTION`.

`flip_feature_spec()` returns `FeatureSpec(name=FEATURE_NAME, model=FlipEngineRow, engine_type="bedrock", system_prompt=..., llm_output_schema=FlipLlmOutput)`.

## Input dataframe contract

Required columns: `REQUIRED_COLUMNS`. Missing column raises `ValueError`.

`political_stance` must be `LEFT_STANCE` or `RIGHT_STANCE` after `str(...)`. Any other value raises `ValueError`.

`llm_toxicity_tier` is required. Persist `str` of the column. Do not store nulls.

Duplicate `record_id` raises `ValueError`.

Sort by `RECORD_ID_COLUMN` with `kind=SORT_KIND` before chunking. `part_index` starts at 0 over that order.

`LabelTask.uri` is `str(record_id)`. `LabelTask.text` is `USER_MESSAGE_TEMPLATE` filled with the opposite stance from `TARGET_GROUP_BY_STANCE` and the original text.

## S3 layout

`run_prefix` is a key prefix that ends in `/`. Example: `experiments/generate_flips_2026_09_08/smoke/`.

| Object | Key |
|--------|-----|
| Part | `{run_prefix}{BATCHES_DIRNAME}/{PART_FILENAME_TEMPLATE}` |
| Errors | `{run_prefix}{ERRORS_FILENAME}` |
| Final | `{run_prefix}{FINAL_FILENAME}` |

Helpers: `part_key(run_prefix, part_index)`, `errors_key(run_prefix)`, `final_key(run_prefix)`. Raise `ValueError` if `run_prefix` does not end with `/` or if `part_index < 0`.

Write each part with `CampaignObjectStore.put_new(..., tags=INTERMEDIATE_ARTIFACT_TAG)`. A second put of the same key must raise `FileExistsError`.

Use `rows_to_parquet_bytes(rows, FLIP_PARQUET_COLUMNS)`. Do not call `write_batch`.

If a chunk has zero successful rows, do not put a parquet part. Append every failed id to `errors.jsonl`. Resume treats those ids as done.

Error lines are JSON objects with `source_record_id`, `error`, `attempts`, `part_index`. Append with `store.append_jsonl`.

## `generate_flips` contract

Every argument is required. No `Optional`, no `None` defaults, no `max_posts`. The Step 2 CLI slices the dataframe and builds the client before calling this function.

```python
def generate_flips(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
    client: BedrockRuntimeClient,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    model_id: str,
) -> FlipRunResult:
```

Behavior:

1. Validate columns and stances. Sort by `RECORD_ID_COLUMN`.
2. Build `LabelTask` rows. Load seen ids from existing parts (`list_keys` on the batches prefix plus `parquet_rows`) union ids in `errors.jsonl`.
3. Chunk the original sorted task list into `batch_size` with stable `part_index`. For each chunk, `pending` is tasks whose uri is not seen. If `pending` is empty, skip. If the part key already exists, skip labeling and skip `put_new`.
4. `label_tasks_collecting_failures(client, model_id, spec, pending, max_concurrency, label_timestamp, max_tokens=max_tokens)`.
5. Join engine rows to the input table on `source_record_id` == `record_id`. Map `flipped_text` → `mirrored_text`. Validate each as `FlipRow`. `put_new` the part when there is at least one success row.
6. Append content-filter and other failures to `errors.jsonl`.
7. When every input id is in a part or in `errors.jsonl`, concatenate parts in `part_index` order with `pd.concat` and `put_new` the final key with **no** intermediate tag. If that object already exists, do not put again. Set `wrote_final` true when the object exists at return. If some ids are still missing, `wrote_final` is false.

`row_count` is the number of rows in all parts. `failed_count` is distinct `source_record_id` values in `errors.jsonl`. `part_count` is the number of parquet part objects.

## Smoke (Phase 4)

Do not add pytest. Do not add files under `tests/` or `shared/flip_generation/tests/`.

Write this given/when/then in the `generate_flips.py` module docstring. Implementers may run it by hand with a fake client after the loop exists; it is not a pytest file.

```text
given a two-row posts frame with required columns and a fake Converse client
and an in-memory store
when generate_flips is called with BATCH_SIZE, MAX_CONCURRENCY, MAX_TOKENS, and DEFAULT_BEDROCK_SONNET_MODEL
then one part object exists
and flips.parquet exists
and FlipRunResult.row_count is 2
and FlipRunResult.wrote_final is true

given the same store and run_prefix
when generate_flips is called again
then the fake client is not called
and FlipRunResult.row_count is 2
```

## Work

Follow `/implement-from-spec`. Full auto. Do not pause after Phase 3. Skip Phase 4 pytest. Phase 4 is the smoke block above.

Phase 1 names `generate_flips` as the caller.

Phase 2 scaffolds the new modules with stub bodies and a thin `generate_flips` that calls validate → tasks → label → write.

Phase 3 locks the three Pydantic models, `FlipRunResult`, file-level constants, and the required-argument `generate_flips` signature.

Phase 5 implements in this order, one commit per unit of work:

1. `max_tokens` on `_converse_once` / `converse_label` / `label_tasks_collecting_failures`
2. Pydantic models and `FLIP_PARQUET_COLUMNS`
3. Prompt + `flip_feature_spec` + `LabelTask` builder
4. `part_key` / `errors_key` / `final_key`
5. `put_new` part writer + resume skip
6. `generate_flips` loop, join, errors, final concat

Phase 6 is complete when the smoke below imports and the modules exist.

## Verification

```bash
PYTHONPATH=. uv run python -c "from shared.flip_generation.generate_flips import BATCH_SIZE, generate_flips; print(BATCH_SIZE)"
```

Expected stdout: `25`

Do not add or run new pytest files for this step.

## Must pass

- `generate_flips` has no optional parameters.
- File-level constants exist; function bodies do not use bare `25`, `10`, or `2048`.
- `build_bedrock_engine` still omits `max_tokens`.
- June flip scripts are unchanged.

## Must fail

- Missing required input column, including `llm_toxicity_tier`.
- Stance other than `left` / `right`.
- Second `put_new` of the same part key.
- Import of `experiments.scaled_mirrors_generation_2026_06_02` from `shared/`.
