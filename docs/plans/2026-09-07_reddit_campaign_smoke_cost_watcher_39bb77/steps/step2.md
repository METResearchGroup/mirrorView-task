# Step 2: Add watcher platform flags and the Reddit smoke caller

## Scope

- **Caller:** `data_platform/generate_features/smoke_reddit_campaign.py` `main`, and `data_platform/generate_features/feature_progress_watcher.py` `main` / `resolve_feature_paths`.
- **Task:** Resolve watcher paths through `FeaturePaths.for_campaign` with `--platform` and `--dataset-id`. Add the Reddit smoke command that labels the shared ten comments, proves interrupt-and-resume, writes four untagged smoke objects, and writes local cost, resume, and S3 check copies.
- **Out of scope:** Editing migrate scripts, Bedrock campaign writer product behavior, registry engine defaults, pytest, all seven live smokes, 400000-row production.

Phase 4 is the watcher `--help` / path check and the live `is_political` command in Step 3, not pytest. Do not add files under `tests/`. Run unattended. Skip Phase 3 approval.

## Files to inspect

- `data_platform/generate_features/smoke_bluesky_campaign.py`
- `data_platform/generate_features/feature_progress_watcher.py`
- `data_platform/generate_features/s3_feature_campaign.py` (`FeaturePaths.for_campaign`, smoke keys, `from_root_uri`)
- `data_platform/generate_features/campaign_engine_map.py` (import only)
- `data_platform/generate_features/campaign_cost_report.py` (Step 1 result)
- `data_platform/generate_features/deterministic_smoke_sample.py` (Step 1 result)
- `data_platform/generate_features/engines/openai_engine.py` (`submit_active_batch`, `OpenAIBatchEngine.label_chunk`)
- `data_platform/generate_features/engines/bedrock_engine.py` (`BedrockConverseEngine.batch_label_records`, `last_usage`, `create_bedrock_runtime_client`, `DEFAULT` model via `lib.constants`)
- `data_platform/generate_features/s3_feature_batches.py` (`attach_provenance`, `validate_q44_rows`)
- `lib/constants.py` (`DEFAULT_LLM_MODEL`, `DEFAULT_BEDROCK_NOVA_MICRO`)

## Files allowed to change

- `data_platform/generate_features/smoke_reddit_campaign.py` (new)
- `data_platform/generate_features/feature_progress_watcher.py`
- `data_platform/generate_features/s3_feature_campaign.py` only if a tiny smoke-path helper is strictly required. Prefer no edit.

## Files forbidden to change

- `data_platform/generate_features/campaign_engine_map.py`
- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/engines/bedrock_campaign.py`
- `data_platform/generate_features/smoke_bluesky_campaign.py` except that the Reddit module may import its helpers
- `data_platform/utils/storage.py`
- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py`
- Any file under `tests/`
- Feature prompt modules
- `webapp/**`, `experiments/**`
- Any GitHub posting code
- `CHANGELOG.md`

Do not add `APPROVED.txt`. Do not drop Reddit Git LFS tracking.

## Watcher contracts

`resolve_feature_paths` becomes:

```python
def resolve_feature_paths(
    campaign_id: str,
    feature: str,
    smoke_prefix: str | None,
    *,
    platform: str = DEFAULT_CAMPAIGN_PLATFORM,
    dataset_id: str = DEFAULT_CAMPAIGN_DATASET_ID,
) -> FeaturePaths:
```

When `smoke_prefix` is None, call `FeaturePaths.for_campaign(campaign_id, feature, platform=platform, dataset_id=dataset_id)`. When `smoke_prefix` is set, keep `FeaturePaths.from_root_uri(smoke_prefix, feature)`.

`main` adds:

- `--platform` default `DEFAULT_CAMPAIGN_PLATFORM` (`bluesky`)
- `--dataset-id` default `DEFAULT_CAMPAIGN_DATASET_ID`

`--help` must show both flags.

When `--platform reddit --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` is passed, `paths.prefix` contains `/reddit/reddit_3d8a2c41`.

The module still prints `github_write_skipped=true` and never posts to GitHub. Grep of the module must show no `gh`, no `PyGithub`, and no HTTP post to `api.github.com`.

## Reddit smoke caller contracts

New module `data_platform/generate_features/smoke_reddit_campaign.py`.

CLI:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --feature <feature> \
  --smoke-prefix <optional-disposable-s3-prefix> \
  --output-dir <git-report-dir>
```

Locked full-run row count inside this caller is `400000`. Do not default this caller to 200000.

Default `--output-dir` is:

`docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}`

### Reuse

Import these from `smoke_bluesky_campaign.py` rather than copying them:

- `SmokePaths`, `SmokeResult`, `InterruptedJob`, `ResumedJob`
- `CountingOpenAIClient`
- `build_smoke_paths` (it already calls `FeaturePaths.for_campaign` with the given `dataset_id`; pass `platform="reddit"` by wrapping if the Bluesky helper hardcodes Bluesky platform)
- `submit_and_interrupt`, `resume_and_collect_rows`, `build_resume_evidence`
- `write_smoke_objects`, `run_s3_checks`, `write_git_copies`, `checks_passed`

If `build_smoke_paths` hardcodes `DEFAULT_CAMPAIGN_PLATFORM` (`bluesky`), do not edit `smoke_bluesky_campaign.py`. In the Reddit module, build paths with `FeaturePaths.for_campaign(..., platform="reddit", dataset_id=dataset_id)` and `FeaturePaths.from_root_uri` using the same overlap rule as Bluesky (`ValueError` when the disposable prefix overlaps the primary feature prefix). That local helper is allowed. Do not change `s3_feature_campaign.py` for this.

Primary-prefix check name in Reddit stdout is `primary_smoke_prefix_touched`, mapped from the Bluesky check `canonical_smoke_prefix_touched` if `run_s3_checks` is reused.

### Engine routing

`engine = campaign_engine_type(campaign_id, feature)`.

OpenAI features use `gpt-5.4-nano` Batch (`DEFAULT_OPENAI_BATCH_ENGINE_CONFIG` / `DEFAULT_LLM_MODEL`). Token usage from `engine.last_batch.usage` plus per-request usage from the batch output file, same as Bluesky.

Bedrock features use Nova Micro (`DEFAULT_BEDROCK_NOVA_MICRO`) through `BedrockConverseEngine`. Token usage from `engine.last_usage` plus per-request usage captured by wrapping `client.converse` so each response's `usage.inputTokens` / `usage.outputTokens` can be paired to a `source_record_id` by matching the user text to the task text. Do not edit `bedrock_engine.py`.

Refuse features that are not in the campaign map for this campaign id.

### Interrupt and resume (inside this module only)

OpenAI: call `submit_and_interrupt`, discard that client, then `resume_and_collect_rows` on a new counting client. Resume must make zero `files.create` and zero `batches.create` calls.

Bedrock: wrap the runtime client and count `converse` calls. First engine labels the ten comments and writes rows plus per-request usage to a local state file, then stops before any S3 write. Second engine reads that file and returns the same rows with zero additional `converse` calls. `resume_ok` is true when resume converse count is 0 and ten rows exist.

Write `resume_evidence.json` to S3 and a Git copy `{feature}_resume_evidence.json`.

### S3 objects

Four untagged objects under `{prefix}{feature}/smoke/` when `--smoke-prefix` is a root URI (Bluesky `from_root_uri` layout), or under the primary `{feature}/smoke/` when `--smoke-prefix` is omitted:

- `input.parquet`
- `output.parquet`
- `cost_report.json`
- `resume_evidence.json`

Smoke never writes `batches/part-*.parquet`. Step 3 live proof must pass `--smoke-prefix` with:

`s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step3_campaign_smoke/`

so the primary prefix is not written.

### Cost report

Call `build_feature_cost_report` with `full_run_row_count=400000` and `engine_type` from the campaign map.

OpenAI pricing: 0.10 / 0.625 and `PRICING_SOURCE_URL`.

Bedrock pricing: 0.035 / 0.14 and `BEDROCK_PRICING_SOURCE_URL`.

### Stdout (order)

```text
smoke_prefix=<uri>
engine_type=<openai|bedrock>
smoke_rows=10
avg_input_tokens=<number>
max_input_tokens=<number>
avg_output_tokens=<number>
max_output_tokens=<number>
estimated_full_run_usd_avg=<number>
estimated_full_run_usd_max=<number>
full_run_row_count=400000
s3_smoke_output_ok=true
s3_smoke_resume_evidence_ok=true
no_batches_prefix_objects=true
primary_smoke_prefix_touched=false
cost_report=<path>
```

Exit 1 when `checks_passed` is false. For a disposable-prefix run, `primary_smoke_prefix_touched` must be false. Do not treat that flag as a pass bit inside `checks_passed` (same as Bluesky).

Local copies under `--output-dir` (temporary during review, deleted in Step 3):

- `{feature}_cost_report.json`
- `{feature}_resume_evidence.json`
- `{feature}_s3_checks.txt`

## Scenarios

1. Given watcher `--help`, when it prints, then the text includes `--platform` and `--dataset-id`.
2. Given `resolve_feature_paths` with the Reddit campaign, `is_political`, `platform='reddit'`, and the pinned dataset id, when it returns, then `'/reddit/reddit_3d8a2c41' in paths.prefix`.
3. Given the watcher module source, when searched for GitHub posting, then it still only records an optional comment id and prints `github_write_skipped=true`.
4. Given OpenAI credentials and the disposable prefix, when the smoke runs for `is_political`, then stdout matches the lines above, `engine_type=openai`, and no primary smoke or batches objects are written.
5. Given a Bedrock feature, when the smoke path runs (later issues, not this PR's live proof), then it uses Bedrock rates, `engine_type=bedrock`, and resume converse count is zero.

## What must pass

- Watcher path check from this plan's Step 3.
- Live `is_political` proof from this plan's Step 3.
- Bluesky smoke module still imports and `load_deterministic_ten_posts` still exists.

## What must fail / stop

- Watcher still resolving Bluesky paths when `--platform reddit` is passed without a dataset override that would keep Bluesky.
- Smoke writing under the primary campaign feature prefix during the disposable proof.
- Smoke writing `batches/part-*.parquet`.
- A second OpenAI Batch job on resume.
- Editing `campaign_engine_map.py` or registry engine defaults.
- Any file under `tests/`.

## Commits

1. Scaffold `smoke_reddit_campaign.py` with Typer flags and stub `run_campaign_smoke`. Add watcher flag signatures that still call the old path until fleshed.
2. Contracts: watcher `resolve_feature_paths` signature, smoke result and summary line names.
3. Flesh watcher `resolve_feature_paths` and CLI flags.
4. Flesh Reddit OpenAI smoke path (sample load, interrupt, resume, S3, summary), enough for the live `is_political` proof.
5. Flesh Reddit Bedrock smoke path (counting converse wrapper, local state resume, Bedrock pricing).

## S3 rules for this step

- Product code may write smoke objects. The only live write allowed in this PR is under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step3_campaign_smoke/`.
- Do not write primary `{feature}/smoke/` or any `batches/` object.
- Deletes of that disposable prefix wait for Step 3.

## Implementation notes

- Always `PYTHONPATH=.`.
- Export `AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"` and `AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"` before any AWS call. Do not echo secrets. No AWS profile.
- `OPENAI_API_KEY` is already set.
- Numpy docstrings on new public functions.
- Do not run all seven live smokes in this PR.
