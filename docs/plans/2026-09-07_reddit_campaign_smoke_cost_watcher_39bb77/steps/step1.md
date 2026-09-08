# Step 1: Extend the ten-comment selector and the mixed-engine cost report

## Scope

- **Caller:** `data_platform/generate_features/deterministic_smoke_sample.py` `load_deterministic_ten_post_ids_for_spec`, and `data_platform/generate_features/campaign_cost_report.py` `main` with `--aggregate` and `--full-run-row-count`.
- **Task:** Accept a `FeaturePlatformSpec` on the ten-row selector, keep Bluesky helpers working, write the committed Reddit ten-id JSON, add mixed-engine parent aggregate fields from the campaign map, and add `--full-run-row-count` with Bluesky default 200000.
- **Out of scope:** Reddit smoke caller, watcher flags, live provider jobs, pytest, registry engine defaults, campaign engine map edits.

Phase 4 for this package is the offline `python -c` and `--help` checks, not pytest. Do not add files under `tests/`. Run unattended. Skip Phase 3 approval.

## Files to inspect

- `data_platform/generate_features/deterministic_smoke_sample.py`
- `data_platform/generate_features/campaign_cost_report.py`
- `data_platform/generate_features/campaign_engine_map.py` (import only)
- `data_platform/generate_features/generate_reddit_features.py` (`REDDIT_SPEC`)
- `data_platform/generate_features/generate_bluesky_features.py` (`BLUESKY_SPEC`)
- `data_platform/generate_features/platform_cli.py` (`FeaturePlatformSpec`, `load_pinned_preprocessed_records`)
- `data_platform/generate_features/smoke_bedrock_engine.py` (`ON_DEMAND_INPUT_USD_PER_MILLION = 0.035`, `ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14`)
- `data_platform/generate_features/smoke_bluesky_campaign.py` (how it calls `load_deterministic_ten_posts` and `build_feature_cost_report`)
- `data_platform/generate_features/feature_progress_watcher.py` (`estimated_cost_to_date` still reads `full_run_post_count`)

## Files allowed to change

- `data_platform/generate_features/deterministic_smoke_sample.py`
- `data_platform/generate_features/campaign_cost_report.py`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json` (new)

## Files forbidden to change

- `data_platform/generate_features/campaign_engine_map.py`
- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/s3_feature_campaign.py`
- `data_platform/generate_features/feature_progress_watcher.py` (Step 2)
- `data_platform/generate_features/smoke_bluesky_campaign.py`
- `data_platform/generate_features/engines/**`
- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` and any other migrate script
- Any file under `tests/`
- `data_platform/data/**`
- Feature prompt modules
- `CHANGELOG.md`

Stage files by explicit path only. Never run `git add -A` or `git add .`.

## Locked identities

| Field | Value |
| ----- | ----- |
| Platform | `reddit` |
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Full-run row count for this campaign | `400000` |
| Bluesky default full-run row count | `200000` (`FULL_RUN_POST_COUNT`) |
| Smoke sample size | `10` |

If Git LFS has not materialized the pinned comments parquet, run this before sample selection:

```bash
git lfs pull --include "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet"
```

## Contracts

### `deterministic_smoke_sample.py`

Keep `SMOKE_POST_COUNT = 10`, `SELECTION_RULE`, and `select_deterministic_sample` unchanged.

Add:

```python
def load_deterministic_ten_posts_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str
) -> pd.DataFrame:
    ...

def load_deterministic_ten_post_ids_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str
) -> list[str]:
    ...

def write_deterministic_ten_post_ids_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str, output: Path
) -> Path:
    ...
```

`load_deterministic_ten_posts` and `load_deterministic_ten_post_ids` stay as Bluesky wrappers that call the `_for_spec` functions with `BLUESKY_SPEC`. `write_deterministic_ten_post_ids` stays a Bluesky wrapper too.

The JSON writer writes:

```json
{
  "dataset_id": "...",
  "preprocessed_run": "...",
  "selection_rule": "Keep rows with non-empty text, sort by ascending source_record_id, take the first ten.",
  "source_record_ids": ["...", "..."]
}
```

Extend `main` with `--platform`. Default `bluesky` keeps the current Bluesky output path behavior. When `--platform reddit`, load `REDDIT_SPEC` and write through `write_deterministic_ten_post_ids_for_spec`. Do not add a second Typer app.

Commit the Reddit ids file at:

`docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json`

### `campaign_cost_report.py`

Keep `FULL_RUN_POST_COUNT = 200_000` and `CAMPAIGN_LLM_FEATURES` (OpenAI names from `FEATURE_REGISTRY`). Do not mutate `FEATURE_REGISTRY`.

Import from `campaign_engine_map.py` only: `campaign_engine_type`, `REDDIT_LLM_FEATURES_CAMPAIGN_ID`, `REDDIT_CAMPAIGN_ENGINE_BY_FEATURE`, `OPENAI_ENGINE_TYPE`, `BEDROCK_ENGINE_TYPE`.

Add Bedrock on-demand constants matching `smoke_bedrock_engine.py`:

- `DEFAULT_BEDROCK_INPUT_USD_PER_MILLION_TOKENS = 0.035`
- `DEFAULT_BEDROCK_OUTPUT_USD_PER_MILLION_TOKENS = 0.14`
- `BEDROCK_PRICING_SOURCE_URL = "https://aws.amazon.com/bedrock/pricing/"`

`BatchPricing` stays the price holder for both engines. OpenAI reports keep `PRICING_SOURCE_URL`. Bedrock reports use `BEDROCK_PRICING_SOURCE_URL`.

`build_feature_cost_report` gains:

- `engine_type: str` written on the report
- `full_run_row_count: int | None = None`. When omitted, use `full_run_post_count`. Write both `full_run_post_count` and `full_run_row_count` with that integer so the watcher can still divide by `full_run_post_count`.
- Keep max token fields `max_input_tokens_per_request` and `max_output_tokens_per_request`.

`aggregate_cost_reports` signature becomes:

```python
def aggregate_cost_reports(
    campaign_id: str,
    smoke_reports_dir: Path,
    features: tuple[str, ...] | None = None,
    full_run_row_count: int = FULL_RUN_POST_COUNT,
) -> dict[str, Any]:
```

Feature list:

- When `features` is passed, use it.
- When `campaign_id == REDDIT_LLM_FEATURES_CAMPAIGN_ID`, use `tuple(REDDIT_CAMPAIGN_ENGINE_BY_FEATURE)`.
- Otherwise use `CAMPAIGN_LLM_FEATURES`.

Each feature entry includes `engine_type` from `campaign_engine_type(campaign_id, feature)`, not from registry defaults.

Parent document fields:

- `campaign_id`
- `generated_at`
- `features_included` (length of entries)
- `openai_features` (count of map entries equal to `openai`)
- `bedrock_features` (count of map entries equal to `bedrock`)
- `full_run_row_count` (the CLI value)
- `features` (one object per feature, including `engine_type` and both estimate fields)
- `total_smoke_cost_usd`
- `total_estimated_full_run_usd_avg`
- `total_estimated_full_run_usd_max`
- `openai_estimated_full_run_usd_avg`
- `openai_estimated_full_run_usd_max`
- `bedrock_estimated_full_run_usd_avg`
- `bedrock_estimated_full_run_usd_max`

`main` adds `--full-run-row-count` with default `FULL_RUN_POST_COUNT` (200000). `--help` must show both `--aggregate` and `--full-run-row-count`.

Stdout for aggregate:

```text
features_included=<n>
openai_features=<n>
bedrock_features=<n>
total_estimated_full_run_usd_avg=<number>
total_estimated_full_run_usd_max=<number>
full_run_row_count=<n>
parent_cost_aggregate.json written
```

The last line still uses `output.name`, so a different output filename still prints `<name> written`. When the output file is `parent_cost_aggregate.json`, the line matches the spec.

Existing Bluesky aggregate without `--full-run-row-count` must still run, with `openai_features=7`, `bedrock_features=0`, `full_run_row_count=200000`, once seven Bluesky reports exist. This step proves that with synthetic temp reports, not live smokes.

## Scenarios (given, when, then)

No pytest. These are the checks Step 3 runs.

1. Given the pinned Reddit comments parquet, when `load_deterministic_ten_post_ids_for_spec(REDDIT_SPEC, pinned dataset, pinned run)` runs, then it returns ten ids and `ids == sorted(ids)`.
2. Given the same run loaded twice, when the selector runs without a feature name, then both calls return the same ids.
3. Given `load_deterministic_ten_post_ids` with Bluesky arguments, when it runs, then it still loads through `BLUESKY_SPEC`.
4. Given seven synthetic cost reports for the Reddit campaign (four `openai`, three `bedrock`) and `--full-run-row-count 400000`, when `--aggregate` runs, then stdout includes `features_included=7`, `openai_features=4`, `bedrock_features=3`, `full_run_row_count=400000`.
5. Given seven synthetic OpenAI reports for the Bluesky campaign and no row-count flag, when `--aggregate` runs, then `full_run_row_count=200000`, `openai_features=7`, `bedrock_features=0`.
6. Given `campaign_cost_report.py --help`, when it prints, then the text includes `--aggregate` and `--full-run-row-count`.

## What must pass

- Offline sample command in `steps/step3.md` of this plan prints `deterministic_ten_comment_ids OK` and `first_id=<id>`.
- The committed JSON has ten sorted `source_record_ids` matching that command.
- `PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py --help` includes `--aggregate` and `--full-run-row-count`.
- Synthetic mixed-engine aggregate for the Reddit campaign id prints the four/three split and 400000.

## What must fail / stop

- Sample ids that differ across calls or that are not sorted.
- Cost math that uses 200000 for the Reddit campaign when `--full-run-row-count 400000` is passed.
- Aggregate that counts engines from `FEATURE_REGISTRY` instead of `campaign_engine_type`.
- Any edit of `registry.py` engine defaults.
- Any file under `tests/`.

## Commits

Frequent commits, no squash. Suggested sequence:

1. Scaffold: add `_for_spec` function signatures as stubs, add `--full-run-row-count` option that is unused, add `engine_type` parameter stub on the cost builder.
2. Contracts: signatures and report/aggregate field names match this file. Bodies still stubbed where new.
3. Test design: this file's scenarios are the spec. No pytest commit. If a commit is required for Phase 4, commit only a comment in the plan, not product code. Prefer to skip a product commit for Phase 4.
4. Flesh `load_deterministic_ten_posts_for_spec` and wrappers.
5. Write and commit `deterministic_ten_comment_ids.json`.
6. Flesh `build_feature_cost_report` engine type and `full_run_row_count`.
7. Flesh `aggregate_cost_reports` mixed-engine parent document and CLI stdout.

## Implementation notes

- `PYTHONPATH=.` on every command.
- Vocabulary: confirm, not freeze. Standardized, not canonical, for new wording. Existing `canonical` aliases may stay. Run, not invoke. Upload and download for S3.
- Numpy docstrings on new public functions.
