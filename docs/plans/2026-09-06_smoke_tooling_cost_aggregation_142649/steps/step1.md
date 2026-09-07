# Step 1: Add the deterministic sample, the cost report module, the smoke caller, and the aggregate command

## Goal

Give every feature run of the campaign one smoke command that labels the same ten posts, proves that an interrupted provider job is resumed instead of resubmitted, writes untagged smoke evidence to S3, and records the token usage and the estimated cost of the full 200,000 post run. Give the parent issue one command that sums the seven per feature estimates.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md`, and the shared layout is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`. Every locked value below is copied from those two files. If this file disagrees with them, they win and this file is wrong.

## Main caller

`data_platform/generate_features/smoke_bluesky_campaign.py` `main`, run as a Typer command. Steps 8 through 14 run it once per feature.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion
```

That command writes the canonical `{feature}/smoke/` prefix and is not run in this PR. The live proof in this file passes `--smoke-prefix` with the disposable prefix and `--output-dir` with the feature report folder.

Happy path through the caller: validate the feature, build the smoke paths, load the ten posts, submit one provider job and save its state, discard that engine, build a new engine that reattaches to the saved job, collect the ten rows with provenance, read per request token usage, write the four smoke objects, run the S3 checks, write the three Git copies, and print the summary lines.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md` | Locked contracts, smoke commands, allowed and forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Smoke object names, Q44 schema, run id |
| `data_platform/generate_features/engines/openai_engine.py` | `OpenAIBatchEngine(spec, run_config, client, engine_config, sleep_fn)`, `label_chunk`, `submit_active_batch`, `create_openai_client`, `DEFAULT_OPENAI_BATCH_ENGINE_CONFIG`, `CUSTOM_ID_PREFIX`, `CUSTOM_ID_INDEX_WIDTH`, `last_batch` |
| `data_platform/generate_features/openai_batch_state.py` | `load_active_batch_state` for the state saved by the submit |
| `data_platform/generate_features/engines/base.py` | `RecordLabelFailure` returned by `label_chunk` |
| `data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.canonical`, `FeaturePaths.from_root_uri`, `CampaignObjectStore.put_new`, `get`, `get_tags`, `list_keys`, `run_id_for_feature` |
| `data_platform/generate_features/s3_feature_batches.py` | `attach_provenance`, `validate_q44_rows`, `q44_columns`, `rows_to_parquet_bytes`, `parquet_rows` |
| `data_platform/generate_features/platform_cli.py` | `load_pinned_preprocessed_records` |
| `data_platform/generate_features/generate_bluesky_features.py` | `BLUESKY_SPEC` |
| `data_platform/generate_features/registry.py` | The seven OpenAI features |
| `data_platform/generate_features/smoke_openai_engine.py` | Existing use of `engine.last_batch.usage` |
| `data_platform/generate_features/models.py` | `FeatureRunConfig`, `LabelTask` |
| `data_platform/utils/platform_specific_columns.py` | `STANDARDIZED_SOURCE_RECORD_ID_COLUMN`, `STANDARDIZED_TEXT_COLUMN` |
| `lib/constants.py` | `REPO_ROOT`, `DEFAULT_LLM_MODEL` |

## Files allowed to change

- `data_platform/generate_features/deterministic_smoke_sample.py` (new)
- `data_platform/generate_features/campaign_cost_report.py` (new)
- `data_platform/generate_features/smoke_bluesky_campaign.py` (new)
- `data_platform/generate_features/s3_feature_campaign.py` (smoke object keys on `FeaturePaths` only)
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json` (new)

`CHANGELOG.md` is edited only in a separate commit after implementation.

## Files forbidden to change

- `tests/**`
- `data_platform/generate_features/engines/**`, `openai_batch_state.py`, `generate_features.py`, `s3_feature_batches.py`, `platform_cli.py`, `generate_bluesky_features.py`, `registry.py`, `models.py`, `metadata.py`
- Feature prompt modules under `data_platform/generate_features/is_*`, `political_stance`, `llm_toxicity_tiered`
- `data_platform/utils/**`, `lib/**`, `webapp/**`, `experiments/**`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`, `campaign_contract.md`, and every step file other than `steps/step6.md`
- Any `APPROVED.txt` or other approval marker, and any code that posts to GitHub or starts agents

Stage files by explicit path only. Never run `git add -A` or `git add .`. Never stage the local smoke output under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion/`.

## S3 and OpenAI rules for this step

- The only S3 writes allowed are under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/`.
- The only S3 deletes allowed are of objects under that same prefix.
- Never write under the canonical `{feature}/smoke/` prefix or any canonical `batches/` prefix.
- Never touch the 53 objects that Step 1 of the epic copied.
- One live OpenAI Batch job of ten requests for `is_news_or_opinion`, and no other provider call.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts`, region `us-east-2` |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Model | `gpt-5.4-nano` (`DEFAULT_LLM_MODEL`) |
| Full run post count | `200000` |
| Ten post rule | Load the pinned run, keep rows whose `text` is not empty after `strip()`, sort by ascending `source_record_id`, take the first ten |
| Canonical smoke keys | `{feature prefix}smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json`, `smoke/resume_evidence.json`, all untagged |
| Smoke prefix override | `--smoke-prefix s3://bucket/root/` puts the feature under `root/{feature}/`, so the smoke objects land at `root/{feature}/smoke/...`. The override must not overlap the canonical feature prefix |
| Run id on every row | `{campaign_id}:{feature}` |
| Q44 columns | `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, and the feature's label field |
| `request_id` | `task-{index:05d}` where `index` is the id's position in the state's `pending_source_record_ids` |
| Pricing | Batch tab of `https://developers.openai.com/api/docs/pricing`. Defaults on 2026-09-06 are `0.10` USD per million input tokens and `0.625` USD per million output tokens |
| Cost per post | `(input_tokens * input_price + output_tokens * output_price) / 1_000_000` |
| Full run estimates | `200000 * cost per post` with the average tokens per request, and again with the maximum tokens per request |
| Git copies | `{output_dir}/{feature}_cost_report.json`, `{output_dir}/{feature}_resume_evidence.json`, `{output_dir}/{feature}_s3_checks.txt`, where `output_dir` defaults to `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/{feature}/` |
| Aggregate input | `{smoke_reports_dir}/{feature}/{feature}_cost_report.json` for each of the seven features whose registry `engine_type` is `openai` |
| Aggregate output | `parent_cost_aggregate.json` with `campaign_id`, `generated_at`, `features` (one entry per feature with both estimates and the smoke cost), `features_included`, `total_estimated_full_run_usd_avg`, `total_estimated_full_run_usd_max`, `total_smoke_cost_usd` |

## Contracts

`data_platform/generate_features/deterministic_smoke_sample.py`:

- `SMOKE_POST_COUNT = 10`
- `select_deterministic_sample(records: pd.DataFrame, count: int = SMOKE_POST_COUNT) -> pd.DataFrame` applies the ten post rule to an already loaded frame and raises `ValueError` when fewer than `count` rows have text.
- `load_deterministic_ten_posts(dataset_id: str, preprocessed_run: str) -> pd.DataFrame` loads the pinned run through `load_pinned_preprocessed_records` and returns the ten full rows.
- `load_deterministic_ten_post_ids(dataset_id: str, preprocessed_run: str) -> list[str]`
- `write_deterministic_ten_post_ids(dataset_id: str, preprocessed_run: str, output: Path) -> Path` writes `{"dataset_id", "preprocessed_run", "selection_rule", "source_record_ids"}` as JSON.
- `main(dataset_id, preprocessed_run, output)` Typer command that calls the writer and prints the output path.

`data_platform/generate_features/campaign_cost_report.py`:

- `PRICING_SOURCE_URL`, `DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS = 0.10`, `DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS = 0.625`, `FULL_RUN_POST_COUNT = 200_000`, `CAMPAIGN_LLM_FEATURES` (the seven OpenAI feature names from the registry, in registry order), `PARENT_AGGREGATE_FILENAME = "parent_cost_aggregate.json"`.
- `@dataclass(frozen=True) class BatchPricing: source_url: str; input_usd_per_million_tokens: float; output_usd_per_million_tokens: float` with `cost_usd(self, input_tokens: int, output_tokens: int) -> float`.
- `@dataclass(frozen=True) class RequestUsage: source_record_id: str; request_id: str; input_tokens: int; output_tokens: int`
- `request_usages_from_output_text(text: str, ordered_ids: list[str]) -> list[RequestUsage]` reads the `usage` block of each batch output line and maps `custom_id` back to `ordered_ids`.
- `build_feature_cost_report(*, campaign_id, dataset_id, preprocessed_run, feature, model, smoke_uri, batch_id, batch_usage: BatchUsage | None, request_usages, pricing, full_run_post_count=FULL_RUN_POST_COUNT) -> dict` returns the per feature report, and raises `ValueError` when `request_usages` is empty.
- `cost_report_path(smoke_reports_dir: Path, feature: str) -> Path` returns `{smoke_reports_dir}/{feature}/{feature}_cost_report.json`.
- `aggregate_cost_reports(campaign_id: str, smoke_reports_dir: Path, features=CAMPAIGN_LLM_FEATURES) -> dict` raises `FileNotFoundError` naming every missing report and `ValueError` when a report's `campaign_id` differs.
- `main(aggregate, campaign_id, smoke_reports_dir, output)` Typer command. Without `--aggregate` it raises a usage error.

`data_platform/generate_features/smoke_bluesky_campaign.py`:

- `DEFAULT_SMOKE_REPORTS_DIR = REPO_ROOT / "docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke"`
- `class CountingOpenAIClient` wraps a client, exposes `files` and `batches`, and counts `files.create` and `batches.create` calls in `calls: Counter`.
- `@dataclass(frozen=True) class SmokeResult` holds the cost report, the resume evidence, the check results, and the local paths written.
- `run_campaign_smoke(*, campaign_id, dataset_id, preprocessed_run, feature, smoke_prefix: str | None, output_dir: Path, pricing: BatchPricing) -> SmokeResult`
- `main(...)` Typer command with `--campaign-id`, `--dataset-id`, `--preprocessed-run`, `--feature`, `--smoke-prefix`, `--output-dir`, `--input-usd-per-million-tokens`, `--output-usd-per-million-tokens`. Prints the ten summary lines and exits with code 1 when any S3 check is false.

`data_platform/generate_features/s3_feature_campaign.py`:

- `SMOKE_DIRNAME = "smoke"`, `SMOKE_INPUT_KEY_SUFFIX`, `SMOKE_COST_REPORT_KEY_SUFFIX`, `SMOKE_RESUME_EVIDENCE_KEY_SUFFIX`, and `FeaturePaths` properties `smoke_prefix`, `smoke_input_key`, `smoke_cost_report_key`, `smoke_resume_evidence_key`.

## Per feature cost report fields

`campaign_id`, `dataset_id`, `preprocessed_run`, `feature`, `run_id`, `model`, `smoke_uri`, `generated_at`, `batch_id`, `request_count`, `pricing` (`source_url`, `input_usd_per_million_tokens`, `output_usd_per_million_tokens`), `batch_usage` (`input_tokens`, `output_tokens`, `total_tokens`, or null), `per_request` (list of `source_record_id`, `request_id`, `input_tokens`, `output_tokens`), `avg_input_tokens_per_request`, `avg_output_tokens_per_request`, `max_input_tokens_per_request`, `max_output_tokens_per_request`, `smoke_cost_usd`, `full_run_post_count`, `estimated_full_run_usd_avg`, `estimated_full_run_usd_max`, `source_record_ids`.

## Resume evidence fields

`feature`, `run_id`, `batch_id`, `input_file_id`, `submitted_at`, `interrupted_at`, `state_at_interrupt` (the saved state with `state` equal to `polling`), `resumed_at`, `submit_calls_before_interrupt` (`files.create` and `batches.create` counts, both 1), `submit_calls_after_resume` (both 0 when the job was reattached), `reattached_same_batch_id` (true when `engine.last_batch.id` equals the saved `batch_id`), `resumed_batch_status`, `rows_written`, `provider_batch_ids_in_output`, `resume_ok` (true when both counts after resume are 0 and the batch id matched and ten rows were written).

## Scenarios (given, when, then)

No pytest is added. These scenarios are the behavior the offline check, the live smoke, and the aggregate command prove.

1. Given the pinned run, when `load_deterministic_ten_post_ids` runs, then it returns ten ids, the list is sorted, and the first id starts with `at://`.
2. Given the same run loaded twice, when the selector runs for two different features, then both get the same ten ids, because the selector does not take the feature as input.
3. Given an empty disposable prefix and `OPENAI_API_KEY`, when the smoke runs for `is_news_or_opinion` with `--smoke-prefix`, then exactly one provider job is created before the interruption, the resumed engine makes zero `files.create` and zero `batches.create` calls, `engine.last_batch.id` equals the saved `batch_id`, and ten rows are written.
4. Given the smoke finished, when the checks run, then `smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json`, and `smoke/resume_evidence.json` exist with no tags, `output.parquet` has ten rows with exactly the Q44 columns, `batches/` under the smoke prefix has no object, and the canonical `is_news_or_opinion/smoke/` prefix is unchanged.
5. Given the per request usages, when the cost report is built, then the averages equal the totals divided by ten, the maximums equal the largest per request values, and the full run estimates equal `200000 * cost per post` under each assumption.
6. Given a `--smoke-prefix` that equals or contains the canonical feature prefix, when the smoke starts, then it raises `ValueError` before any S3 or OpenAI call.
7. Given seven report files under a temporary directory, when the aggregate command runs, then it prints `features_included=7`, both totals, and `parent_cost_aggregate.json written`, and the output file holds one entry per feature.
8. Given six report files, when the aggregate command runs, then it raises `FileNotFoundError` naming the missing seventh path and writes nothing.

## Ordered implementation work

1. Scaffold the three new modules with stub bodies and a thin `main` in each, plus the `FeaturePaths` smoke keys. Commit.
2. Fill in the signatures above with stub bodies. Commit.
3. Write the smoke caller's summary print lines and check composition against the stubs, as the executable spec of the caller. Commit.
4. Implement `deterministic_smoke_sample.py`, run the offline check, write `deterministic_ten_post_ids.json`. Commit.
5. Implement pricing, `RequestUsage` parsing, and `build_feature_cost_report`. Commit.
6. Implement `aggregate_cost_reports` and the aggregate command. Commit.
7. Implement the submit, interrupt, and resume path and the row collection in `run_campaign_smoke`. Commit.
8. Implement the S3 writes, the S3 checks, and the Git copies. Commit.
9. Run the live smoke under the disposable prefix. Record the observed output for the PR body. Do not commit the local `reports/smoke/is_news_or_opinion/` output.
10. Run the aggregate command against seven temporary copies of the observed report under `/tmp`. Delete the temporary output.
11. Delete every object under the disposable prefix with boto3, list it to show it is empty, and list the canonical `is_news_or_opinion/smoke/` prefix to show it is absent.
12. Run `uv run pytest -q`. Expect 631 passed.
13. Delete the local `reports/smoke/is_news_or_opinion/` folder from the working tree.

## Exact commands with expected output

### Offline deterministic sample check

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.deterministic_smoke_sample import load_deterministic_ten_post_ids
ids = load_deterministic_ten_post_ids(
    'bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73',
    '2026_09_03-23:51:30',
)
assert len(ids) == 10
assert ids == sorted(ids)
print('deterministic_ten_post_ids OK')
print('first_id=' + ids[0])
"
```

Expected stdout:

```text
deterministic_ten_post_ids OK
first_id=at://...
```

### Write the committed ids file

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/deterministic_smoke_sample.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json
```

Expected: the command prints the output path, and the file holds ten ids in ascending order.

### Live single feature tooling proof (requires `OPENAI_API_KEY`)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/

PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --output-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion
```

Expected stdout:

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/
smoke_rows=10
avg_input_tokens=<number>
max_input_tokens=<number>
avg_output_tokens=<number>
max_output_tokens=<number>
estimated_full_run_usd_avg=<number>
estimated_full_run_usd_max=<number>
s3_smoke_output_ok=true
s3_smoke_resume_evidence_ok=true
no_batches_prefix_objects=true
canonical_smoke_prefix_touched=false
cost_report=docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion/is_news_or_opinion_cost_report.json
```

### Aggregate command against seven temporary copies

```bash
cd /workspace
mkdir -p /tmp/step6_aggregate
for f in is_news_or_opinion is_political is_likely_spam is_self_contained is_structurally_complete political_stance llm_toxicity_tiered; do
  mkdir -p /tmp/step6_aggregate/$f
  sed "s/\"feature\": \"is_news_or_opinion\"/\"feature\": \"$f\"/" \
    docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion/is_news_or_opinion_cost_report.json \
    > /tmp/step6_aggregate/$f/${f}_cost_report.json
done

PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --smoke-reports-dir /tmp/step6_aggregate \
  --output /tmp/step6_aggregate/parent_cost_aggregate.json
```

Expected stdout:

```text
features_included=7
total_estimated_full_run_usd_avg=<number>
total_estimated_full_run_usd_max=<number>
parent_cost_aggregate.json written
```

Then `rm -rf /tmp/step6_aggregate`.

### Disposable prefix cleanup (required before merge)

The `aws` CLI is not installed in this environment, so the cleanup uses boto3 with the same effect.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
import boto3
s3 = boto3.client('s3', region_name='us-east-2')
bucket = 'mirrorview-experimental-artifacts'
prefix = 'data_platform/data/_smoke/step6_campaign_smoke/'
keys = [o['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix) for o in page.get('Contents', [])]
for key in keys:
    print('delete:', key)
if keys:
    s3.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': k} for k in keys]})
left = s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get('KeyCount', 0)
print('remaining_under_disposable_prefix=', left)
canonical = 'data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/smoke/'
print('canonical_smoke_key_count=', s3.list_objects_v2(Bucket=bucket, Prefix=canonical).get('KeyCount', 0))
"
```

Expected: one `delete:` line per smoke object, then `remaining_under_disposable_prefix= 0` and `canonical_smoke_key_count= 0`.

### Existing suite

```bash
cd /workspace
uv run pytest -q
```

Expected: `631 passed`.

## Must pass

- The offline check prints `deterministic_ten_post_ids OK` and a first id that starts with `at://`.
- The live smoke prints the thirteen expected lines with `s3_smoke_output_ok=true`, `s3_smoke_resume_evidence_ok=true`, `no_batches_prefix_objects=true`, and `canonical_smoke_prefix_touched=false`.
- The resume evidence records zero `files.create` and zero `batches.create` calls after the resume and the same `batch_id` before and after.
- The aggregate command prints `features_included=7` and writes one entry per feature.
- The cleanup prints `remaining_under_disposable_prefix= 0` and `canonical_smoke_key_count= 0`.
- `uv run pytest -q` reports 631 passed with no test file changes.

## Must fail

- A smoke prefix that overlaps the canonical feature prefix.
- Fewer than ten label rows, or a row without the full Q44 column set.
- Any write under `batches/`.
- Any tag on a smoke object.
- An aggregate run with fewer than seven readable reports.
