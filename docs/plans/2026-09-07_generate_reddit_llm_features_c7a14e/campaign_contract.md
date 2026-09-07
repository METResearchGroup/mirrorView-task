# Reddit LLM features campaign contract

A wrong bucket path or engine assignment forces a 400,000-row rerun, so every step file repeats only the values its pull request needs and `campaign_contract.md` holds the rest.

## Pinned identities

| Field | Value |
|-------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Pinned preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | `400000` comments (not posts) |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Batch size | `2000` |
| Expected rows per feature | `400000` |
| Batch count | `200` (`part-00000` through `part-00199`) |
| Full run row constant | `FULL_RUN = 400000` |

Preprocessed input object:

`s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet`

Copy to S3 policy: upload only `comments.parquet`. Keep Git LFS for local copies. Keep `dataset.json` in git with format `parquet`.

## Campaign engine map

The campaign engine map overrides engines per feature for `reddit_2026_09_03_233928_llm_features_v1` only, so implementers do not change global `FEATURE_REGISTRY` defaults.

| Feature | Engine | Model id |
|---------|--------|----------|
| `is_news_or_opinion` | OpenAI Batch | `gpt-5.4-nano` |
| `is_political` | OpenAI Batch | `gpt-5.4-nano` |
| `political_stance` | OpenAI Batch | `gpt-5.4-nano` |
| `llm_toxicity_tiered` | OpenAI Batch | `gpt-5.4-nano` |
| `is_likely_spam` | Bedrock Converse | `us.amazon.nova-micro-v1:0` |
| `is_self_contained` | Bedrock Converse | `us.amazon.nova-micro-v1:0` |
| `is_structurally_complete` | Bedrock Converse | `us.amazon.nova-micro-v1:0` |

Record `engine_type` on `manifest.json` and local `metadata.json`. Do not add an `engine_type` column to feature Parquet output.

Reuse registry prompts for all seven features.

## S3 feature root and layout

Feature root (exact):

`s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/`

Per feature `{feature}` under that root:

| Object | Path | Notes |
|--------|------|-------|
| Smoke input | `{feature}/smoke/input.parquet` | Ten-comment deterministic sample input. Untagged. |
| Smoke output | `{feature}/smoke/output.parquet` | Ten labeled rows with label metadata columns. Untagged. |
| Smoke cost report | `{feature}/smoke/cost_report.json` | Token and pricing estimates. Untagged. |
| Smoke resume evidence | `{feature}/smoke/resume_evidence.json` | Interrupt and resume proof. Untagged. |
| Active OpenAI state | `{feature}/active_openai_batch.json` | OpenAI features only. Mutable. Untagged. Conditional atomic replace. |
| Active Bedrock state | `{feature}/active_bedrock_job.json` | Bedrock features only. Mutable. Untagged. Conditional atomic replace. Resume cursor for the current part. |
| Batch parquet | `{feature}/batches/part-NNNNN.parquet` | Zero-based five-digit index. Immutable once written. Tagged `intermediate-artifact=true`. |
| Final parquet | `{feature}/final.parquet` | One consolidated file per feature. Untagged. |
| Manifest | `{feature}/manifest.json` | SHA-256 digests only. Records `engine_type`. Bedrock manifests may include `openai_content_filter_retry` after a content-filter retry. Untagged. Conditional atomic replace. |
| Progress | `{feature}/progress.jsonl` | Logical append via read, append, conditional replace. Untagged. |
| Errors | `{feature}/errors.jsonl` | Same append semantics when needed. Bedrock content-filter failures use reason `bedrock_content_filter`. Untagged. |
| Watcher state | `{feature}/watcher.json` | Rolling GitHub comment id and last posted 10k milestone. Untagged. Conditional atomic replace. |

Wide outputs under the same feature root:

| Object | Path |
|--------|------|
| Wide parquet | `wide/features.parquet` |
| Wide manifest | `wide/manifest.json` |

Forbidden layout elements:

- No `campaigns/` prefix.
- No `shards/` directory or `shard_*` object names.
- No `final/` subdirectory or per-feature final filenames such as `final/is_news_or_opinion.parquet`.
- No `manifest/` directory or `manifest.sha256.json`.
- No `progress/` directory.
- No per-run timestamp subfolder under a feature prefix.
- No production `batches/part-*.parquet` written during smoke. Smoke never writes production batch objects.
- No GitHub writes from repository code.
- No `APPROVED.txt` or other repository approval file.
- No dropping Git LFS for the pinned comments parquet.
- No global change to Bluesky campaign defaults.
- No Perspective feature `is_toxic_tiered` in this campaign.

Intermediate batch objects only carry S3 object tag `intermediate-artifact=true`. Smoke artifacts, active state files, final parquet, manifests, progress, errors, watcher state, wide outputs, and reports are untagged.

No new lifecycle issue is required. The existing 30-day lifecycle rule already expires objects tagged `intermediate-artifact=true` under `data_platform/data/`.

## Smoke S3 evidence (Step 3 and Steps 4 through 10 Phase A)

Smoke writes exactly these untagged objects under `{feature}/smoke/`:

- `input.parquet` (ten deterministic comments)
- `output.parquet` (ten label rows)
- `cost_report.json`
- `resume_evidence.json`

Smoke runs through `smoke_reddit_campaign.py` with one deliberate interruption and resume. Feature run steps must not repeat the interruption procedure.

Smoke never writes `batches/part-00000.parquet` or any other production batch object.

Temporary Git copies of smoke evidence live under `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}/` during Phase A and are deleted before merge. S3 smoke evidence under `{feature}/smoke/` remains.

### Deterministic ten-comment sample (shared by all seven features)

1. Load pinned preprocessed run `2026_09_03-23:39:28`.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

## Production batch schedule (after parent approval)

After parent approval, each feature writes exactly 200 batch objects totaling 400,000 rows.

| Part | Row composition |
|------|-----------------|
| `part-00000` | Ten unchanged smoke output rows (original smoke `batch_id` and `request_id` preserved) plus 1,990 new labeled rows |
| `part-00001` through `part-00199` | 2,000 new labeled rows each |

OpenAI features run exactly 200 provider jobs for `part-00000` through `part-00199` at 2,000 rows per job except the first job labels 1,990 new comments only. Bedrock features process one 2,000-comment part per serial part write with one process and eight threads (eight threads per process).

Bedrock concurrency limits:

- One process and eight threads per Bedrock part.
- At most three Bedrock feature agents may run in parallel (24 in-flight requests).
- Never run six or more Bedrock processes at once, because throughput experiments found four processes at eight threads peaked at 32 in-flight requests and six or eight processes were throttled.

Do not relabel the ten smoke comments. Do not run smoke twice.

## Active OpenAI batch state (`active_openai_batch.json`)

OpenAI features persist campaign state at `{feature}/active_openai_batch.json` in S3. The state contract matches the Bluesky epic Step 4 definition.

Before the first `batches.retrieve` poll call, conditionally write (If-Match when object exists) a JSON object with at least:

| Field | Meaning |
|-------|---------|
| `input_file_id` | OpenAI files id for the submitted batch input |
| `batch_id` | OpenAI Batch provider id |
| `logical_batch_index` | Zero-based part index this job will populate |
| `pending_source_record_ids` | Ordered ids still expected from this provider job |
| `attempt_count` | Per-job attempt counter |
| `state` | `polling`, `writing`, or `terminal` |

On restart, reload `active_openai_batch.json` and reattach to the same `batch_id` when provider status is non-terminal. Never call `files.create` or `batches.create` again for that in-flight job.

Delete `active_openai_batch.json` only after all successful rows from that provider job are durably written to an immutable batch object and recorded in `manifest.json`.

## Active Bedrock job state (`active_bedrock_job.json`)

Bedrock features persist campaign state at `{feature}/active_bedrock_job.json` in S3.

Before polling or writing a part, conditionally write (If-Match when object exists) a JSON object with at least:

| Field | Meaning |
|-------|---------|
| `logical_batch_index` | Zero-based part index in progress |
| `pending_source_record_ids` | Ordered ids still expected for the current part |
| `attempt_count` | Per-part attempt counter |
| `state` | `running`, `writing`, or `terminal` |

On restart, reload `active_bedrock_job.json` and resume the current part from the saved cursor. Delete `active_bedrock_job.json` only after the part is durably written and recorded in `manifest.json`.

## Bedrock content-filter retry

When Bedrock returns a content-filter failure for a comment, the operator pays twice if OpenAI Batch succeeds on retry, so the manifest records retry ids even though `engine_type` stays `bedrock`.

1. Append one line to `errors.jsonl` with reason `bedrock_content_filter` and the `source_record_id`.
2. Retry that comment through OpenAI Batch inside the same feature command run.
3. Keep `engine_type=bedrock` on `manifest.json` and add an `openai_content_filter_retry` block that records which ids were retried and the OpenAI batch metadata.

Other Bedrock failures stay failed. Do not switch the whole feature to OpenAI.

## S3 logical append and conditional replace

`progress.jsonl` and `errors.jsonl` use logical append:

1. One feature writer reads existing object bytes (empty if missing).
2. Appends one or more complete newline-terminated JSON records.
3. Conditionally replaces the whole object using S3 `If-Match` with the prior object ETag for concurrency control only.

SHA-256 remains the content integrity check for parquet and manifest bytes. Never accept S3 ETag as a content hash.

If a conditional put fails, retry from the latest object bytes and ETag.

S3 atomic object replacement can leave the prior object visible on interruption. Immutable batch objects plus `manifest.json` are the source of truth. Resume may reconstruct missing observability events in `progress.jsonl` or `errors.jsonl` from batch and manifest state.

`manifest.json`, `watcher.json`, `active_openai_batch.json`, and `active_bedrock_job.json` also use conditional atomic whole-object replacement with `If-Match` ETag for concurrency control.

## Deterministic run id and immutability

Per-feature run id (stored in every row as `run_id`):

`reddit_2026_09_03_233928_llm_features_v1:{feature}`

Restart and resume reuse the same `run_id` and the same feature prefix. Feature prefixes are immutable except:

- Logical append to `progress.jsonl` and `errors.jsonl`.
- Conditional atomic replacement of `manifest.json`, `watcher.json`, `active_openai_batch.json`, and `active_bedrock_job.json`.
- New batch objects with the next unused `part-NNNNN.parquet` index.

Existing completed batch objects are never overwritten.

## Seven features

| Feature | Raw label field | Pydantic model (label subset) | Accepted values |
|---------|-----------------|------------------------------|-----------------|
| `is_news_or_opinion` | `category` | `IsNewsOrOpinionModel` | `news`, `opinion`, `neither` |
| `is_political` | `is_political` | `IsPoliticalModel` | boolean |
| `is_likely_spam` | `is_likely_spam` | `IsLikelySpamModel` | boolean |
| `is_self_contained` | `is_self_contained` | `IsSelfContainedModel` | boolean |
| `is_structurally_complete` | `is_structurally_complete` | `IsStructurallyCompleteModel` | boolean |
| `political_stance` | `political_stance` | `PoliticalStanceModel` | `left`, `right`, `neutral`, `unclear` |
| `llm_toxicity_tiered` | `toxicity_tier` | `LlmToxicityTieredModel` | `low`, `medium`, `high` |

Do not run Perspective feature `is_toxic_tiered` in this campaign.

## Row schema (feature output)

Every row in `smoke/output.parquet`, `batches/part-*.parquet`, and `final.parquet` must contain exactly these columns:

| Column | Meaning |
|--------|---------|
| `source_record_id` | Pinned preprocessed comment id |
| `run_id` | `reddit_2026_09_03_233928_llm_features_v1:{feature}` |
| `batch_id` | Provider batch or part id for the batch that produced the row |
| `request_id` | Provider request id for the row |
| `attempt_count` | Integer attempt count for this row (1 through 4) |
| `label_timestamp` | UTC timestamp from `lib.timestamp_utils.get_current_timestamp` |
| `{label_field}` | The feature's raw label column from the table above |

Validation applies the feature Pydantic model to the label-field subset and separately validates label metadata columns. Do not add `engine_type` to Parquet rows.

## Campaign CLI

Extend `data_platform/generate_features/generate_reddit_features.py` through `platform_cli` with `--campaign-id` and `--preprocessed-run` for production campaign mode. The `generate_reddit_features()` Python API has no `campaign_id`; campaign mode is CLI only.

Campaign mode rules:

- Pass exactly one value to `--features`.
- Pass `--batch-size 2000`.
- Pass `--platform reddit` and `--dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079`.
- Campaign mode automatically resumes feature state in its feature prefix on restart.
- Do not add `run_reddit_llm_campaign.py`, `--resume`, `APPROVED.txt`, or a timestamp `--checkpoint`.

Feature path helpers default today to Bluesky. Campaign callers must pass `platform=reddit` and `dataset_id`. The old `canonical` alias on feature paths is broken; use or fix `for_campaign`.

Example OpenAI feature command:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --platform reddit \
  --features is_news_or_opinion \
  --batch-size 2000
```

OpenAI features keep one blocking OpenAI Batch job active per feature at a time. Bedrock features keep one part writer active per feature at a time with one process and eight threads.

## Smoke tooling and approval flow (Step 3)

Step 3 adds reusable tooling only:

- `data_platform/generate_features/smoke_reddit_campaign.py`
- A mixed-engine aggregation command that sums seven per-feature cost estimates across OpenAI Batch and Bedrock on-demand pricing

Step 3 does not run full 400k labeling and does not add a file-based approval marker.

Steps 4 through 10 (each in its own feature PR):

1. Run `smoke_reddit_campaign.py` once for that feature (includes deliberate interruption and resume).
2. Commit temporary Git smoke evidence under `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}/`.
3. Post the estimated full-run cost to that feature's GitHub issue.
4. Pause until all seven feature issues have estimates and the parent campaign issue has one mixed-engine aggregate estimate plus explicit human approval.

Human approval is recorded on the parent GitHub issue only, because a merged pull request or passing smoke alone does not authorize production labeling. No `APPROVED.txt` or other repository approval file exists.

## Cost pricing

| Engine | Input price | Output price | Notes |
|--------|-------------|--------------|-------|
| OpenAI Batch `gpt-5.4-nano` | $0.10 per million tokens | $0.625 per million tokens | Batch tab pricing |
| Bedrock on-demand `us.amazon.nova-micro-v1:0` | $0.035 per million tokens | $0.14 per million tokens | Converse on-demand pricing in `us-east-2` |

Full-run estimates multiply `FULL_RUN = 400000` comments by per-comment token averages and maximums from smoke. The mixed-engine aggregate command sums OpenAI and Bedrock estimates into one parent total.

## Progress and watcher (Step 3)

`progress.jsonl` is the only progress event file. Each append records durable row totals and batch metadata after a batch lands.

`watcher.json` stores:

- `github_comment_id` (rolling feature-issue comment)
- `last_posted_milestone` (last 10k boundary posted: 10000, 20000, …, 400000)

The watcher CLI accepts `--platform` and `--dataset-id`, prints a prepared markdown report, and never calls GitHub write APIs. A restartable agent outside repository code posts or updates one feature-issue comment through authenticated GitHub integration.

## Permanent report paths

| Report | Path |
|--------|------|
| Per-feature | `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/{feature}_run_report.md` |
| Wide consolidation | `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/wide_run_report.md` |

Temporary Git smoke evidence (committed during Phase A, deleted before merge):

`docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}/`

## Wide table (Step 11)

Wide output: exactly sixteen columns in this order.

Nine preprocessed comment columns:

`comment_fullname`, `record_id`, `author`, `body`, `created_at`, `sync_timestamp`, `text`, `author_handle`, `source_record_id`

Seven aliased label columns:

| Wide column | Source feature | Source column |
|-------------|----------------|---------------|
| `news_or_opinion_category` | `is_news_or_opinion` | `category` |
| `is_political` | `is_political` | `is_political` |
| `is_likely_spam` | `is_likely_spam` | `is_likely_spam` |
| `is_self_contained` | `is_self_contained` | `is_self_contained` |
| `is_structurally_complete` | `is_structurally_complete` | `is_structurally_complete` |
| `political_stance` | `political_stance` | `political_stance` |
| `llm_toxicity_tier` | `llm_toxicity_tiered` | `toxicity_tier` |

Join all seven feature outputs and the preprocessed comments on `source_record_id` through `consolidate_reddit_llm_campaign.py`, then run curation from `data_platform/curate/configs/reddit/mirrorview.yaml`.

Wide manifest links all seven per-feature manifests plus preprocessed input hash.

Forbidden wide columns: `toxicity_tier`, `toxicity_prob`, `label_timestamp`, `run_id`, any Perspective column.

## Step dependencies

| Step | Depends on | Can run parallel with | Delivers |
|------|------------|----------------------|----------|
| 1 | none | 2 | S3 copy of pinned `comments.parquet` |
| 2 | none | 1 | Campaign engine map and Bedrock S3 campaign path |
| 3 | 1, 2 | none (after 1 and 2) | Reddit smoke, mixed cost aggregate, watcher platform flags |
| 4 through 10 | 1, 2, 3, parent sign-off | each other (after sign-off) | One feature run each (docs-only PRs for Steps 4 through 10) |
| 11 | 4 through 10 | none | Wide join and MirrorView curation export |

Steps 4 through 10 require Step 3 smoke tooling, Step 2 engine map, Step 1 S3 input, and explicit parent issue sign-off. Steps 6 through 8 are Bedrock features and share the Bedrock concurrency limits.

## Verification rules

- Content hashes are SHA-256 lowercase hex of full object bytes. Never accept S3 ETag as a content hash.
- S3 ETag with `If-Match` is permitted only for concurrency control on conditional replace of `progress.jsonl`, `errors.jsonl`, `manifest.json`, `watcher.json`, `active_openai_batch.json`, and `active_bedrock_job.json`.
- No automated tests are added or run for Steps 4 through 10. Use live smoke and basic runtime checks only.
- Temporary Git smoke files may be committed during review and must be removed before merge.

## Hash and manifest rules

`manifest.json` at each feature prefix and `wide/manifest.json` use SHA-256 hex digests only. Do not use MD5, ETag alone, or size-only checks as acceptance gates.

## Parent sign-off checklist

Do not start any 400,000-comment feature run in Steps 4 through 10 until all of the following are true:

- The prerequisite implementation pull request for Steps 1 through 3 has been reviewed and approved.
- All seven ten-comment smoke runs and per-feature cost estimates have been posted.
- The mixed-engine aggregate campaign cost estimate has been posted to the parent issue.
- The repository owner has explicitly signed off in the parent issue on the prerequisite pull request, smoke results, and aggregate cost estimate.

A merged pull request or a passing smoke run alone is not permission to start production labeling, because the explicit owner sign-off in the parent issue is mandatory.

---

## GitHub issue body drafts

Child issue bodies live in each step file under `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/steps/`.

### Parent issue body

The campaign labels 400,000 pinned Reddit comments from PR #162 with seven mixed-engine LLM features. Operators upload preprocessed `comments.parquet` to `mirrorview-experimental-artifacts` while Git LFS keeps the local copy, reusing the Bluesky epic S3 backend, OpenAI Batch resume, 2,000-row Parquet writer, progress watcher, and 30-day lifecycle rule for tagged batch objects.

Four features run on OpenAI Batch with `gpt-5.4-nano`. Three features run on Amazon Bedrock Converse with `us.amazon.nova-micro-v1:0`. Each feature run writes 200 immutable 2,000-row Parquet batch objects, a final feature Parquet file, a hash manifest, progress records, and a permanent run report. Step 11 joins the seven outputs with all nine preprocessed comment columns and runs the MirrorView curation export.

Dataset id is `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` and preprocessed run is `2026_09_03-23:39:28`. Campaign artifacts live under `s3://mirrorview-experimental-artifacts/data_platform/data/` with campaign id `reddit_2026_09_03_233928_llm_features_v1` and one isolated prefix per feature. OpenAI features persist provider job IDs in `active_openai_batch.json` before polling and resume the existing provider job after interruption. Bedrock features use `active_bedrock_job.json` with one process and eight threads per part, and at most three Bedrock feature agents may run in parallel.

Each child issue maps to one future pull request. The repository owner records production approval on the parent issue only. Do not start any 400,000-comment feature run until Steps 1 through 3 have merged, all seven smoke runs and per-feature cost estimates are posted, the mixed-engine aggregate estimate is posted here, and the repository owner signs off in a comment on the prerequisite pull request, smoke results, and aggregate cost.

Plan step: `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/plan.md`

Done when:

1. The pinned preprocessed `comments.parquet` is available from S3 with a verified hash, and Git LFS still holds the local copy.
2. Seven feature issues each produce exactly 400,000 unique, valid LLM labels across 200 batch objects and one permanent run report.
3. OpenAI features resume without duplicate provider jobs or duplicate charges. Bedrock features resume from `active_bedrock_job.json` without exceeding three parallel agents or six Bedrock processes.
4. Each issue reports progress every 10,000 durable records and records estimated and actual cost.
5. One wide Parquet artifact contains the nine pinned comment columns and all seven LLM feature outputs, and the MirrorView curation export is written from `data_platform/curate/configs/reddit/mirrorview.yaml`.
6. Intermediate batches expire after 30 days under the existing lifecycle rule, while final artifacts and run metadata remain in S3.

## Children

- [ ] Step 1: Copy the pinned Reddit preprocessed comments parquet to S3
- [ ] Step 2: Add a campaign engine map and Bedrock S3 campaign path
- [ ] Step 3: Add Reddit campaign smoke, mixed-engine cost aggregate, and watcher platform flags
- [ ] Step 4: Generate is_news_or_opinion for 400,000 Reddit comments
- [ ] Step 5: Generate is_political for 400,000 Reddit comments
- [ ] Step 6: Generate is_likely_spam for 400,000 Reddit comments
- [ ] Step 7: Generate is_self_contained for 400,000 Reddit comments
- [ ] Step 8: Generate is_structurally_complete for 400,000 Reddit comments
- [ ] Step 9: Generate political_stance for 400,000 Reddit comments
- [ ] Step 10: Generate llm_toxicity_tiered for 400,000 Reddit comments
- [ ] Step 11: Consolidate seven Reddit LLM features and write the MirrorView curated export
