# Bluesky LLM features campaign contract

This file is the single cross-step contract for epic `2026-09-05_generate_bluesky_llm_features_4d8a7c`. Every implementation and run step that touches this campaign must match these values. Each step file also repeats the values its delegated task needs so the task cannot be misread.

## Pinned identities

| Field | Value |
|-------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Pinned preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | `200000` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Model id | `gpt-5.4-nano` |
| Batch size | `2000` |
| Expected rows per feature | `200000` |
| Canonical batch count | `100` (`part-00000` through `part-00099`) |

Preprocessed input object:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet`

## S3 feature root and layout

Feature root (exact):

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/`

Per feature `{feature}` under that root:

| Object | Path | Notes |
|--------|------|-------|
| Smoke input | `{feature}/smoke/input.parquet` | Ten-post deterministic sample input. Untagged. |
| Smoke output | `{feature}/smoke/output.parquet` | Ten labeled rows with Q44 columns. Untagged. |
| Smoke cost report | `{feature}/smoke/cost_report.json` | Token and pricing estimates. Untagged. |
| Smoke resume evidence | `{feature}/smoke/resume_evidence.json` | Interrupt and resume proof. Untagged. |
| Active provider state | `{feature}/active_openai_batch.json` | Mutable. Untagged. Conditional atomic replace. |
| Batch parquet | `{feature}/batches/part-NNNNN.parquet` | Zero-based five-digit index. Immutable once written. Tagged `intermediate-artifact=true`. |
| Final parquet | `{feature}/final.parquet` | One consolidated file per feature. Untagged. |
| Manifest | `{feature}/manifest.json` | SHA-256 digests only. Untagged. Conditional atomic replace. |
| Progress | `{feature}/progress.jsonl` | Logical append via read, append, conditional replace. Untagged. |
| Errors | `{feature}/errors.jsonl` | Same append semantics when needed. Untagged. |
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
- No `metadata.json` at the feature prefix (run identity lives in `manifest.json` and row provenance).
- No canonical `batches/part-*.parquet` written during smoke. Smoke never writes production batch objects.

Intermediate batch objects only carry S3 object tag `intermediate-artifact=true`. Smoke artifacts, `active_openai_batch.json`, final parquet, manifests, progress, errors, watcher state, wide outputs, and reports are untagged.

## Smoke S3 evidence (Steps 6 and 8 through 14 Phase A)

Smoke writes exactly these untagged objects under `{feature}/smoke/`:

- `input.parquet` (ten deterministic posts)
- `output.parquet` (ten Q44 label rows)
- `cost_report.json`
- `resume_evidence.json`

Smoke performs one deliberate interruption and resume through `smoke_bluesky_campaign.py`. That single invocation records `resume_evidence.json`. Feature run steps must not repeat the interruption procedure.

Smoke never writes `batches/part-00000.parquet` or any other canonical batch object.

Temporary Git copies of smoke evidence live under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/{feature}/` during Phase A and are deleted before merge. S3 smoke evidence under `{feature}/smoke/` remains.

## Production batch schedule (after parent approval)

After parent approval, each feature runs exactly 100 provider jobs and writes exactly 100 canonical batch objects totaling 200,000 rows.

| Canonical part | Provider job size | Row composition |
|----------------|-------------------|-----------------|
| `part-00000` | 1,990 new posts | Ten unchanged smoke output rows (original smoke `batch_id` and `request_id` preserved) plus 1,990 new labeled rows |
| `part-00001` through `part-00099` | 2,000 new posts each | All new labeled rows |

The first provider job after approval labels 1,990 posts only. Its successful rows are combined with the ten smoke output rows into immutable `batches/part-00000.parquet` (2,000 rows total). The next 99 provider jobs each process 2,000 posts and each write one canonical batch object.

`manifest.json` batch entry for `part_index=0` may list both the smoke provider `batch_id` and the first production provider `batch_id` because those ten rows retain smoke provenance.

Do not relabel the ten smoke posts. Do not run smoke twice.

## Active OpenAI batch state (`active_openai_batch.json`)

Step 4 defines the state contract independent of storage backend. Step 5 persists campaign state at `{feature}/active_openai_batch.json` in S3.

Before the first `batches.retrieve` poll call, conditionally write (If-Match when object exists) a JSON object with at least:

| Field | Meaning |
|-------|---------|
| `input_file_id` | OpenAI files id for the submitted batch input |
| `batch_id` | OpenAI Batch provider id |
| `logical_batch_index` | Zero-based canonical part index this job will populate |
| `pending_source_record_ids` | Ordered ids still expected from this provider job |
| `attempt_count` | Per-job attempt counter |
| `state` | `polling`, `writing`, or `terminal` |

On restart, reload `active_openai_batch.json` and reattach to the same `batch_id` when provider status is non-terminal. Never call `files.create` or `batches.create` again for that in-flight job.

Delete `active_openai_batch.json` only after all successful rows from that provider job are durably written to an immutable batch object and recorded in `manifest.json`.

## S3 logical append and conditional replace

`progress.jsonl` and `errors.jsonl` use logical append:

1. One feature writer reads existing object bytes (empty if missing).
2. Appends one or more complete newline-terminated JSON records.
3. Conditionally replaces the whole object using S3 `If-Match` with the prior object ETag for concurrency control only.

SHA-256 remains the content integrity check for parquet and manifest bytes. Never accept S3 ETag as a content hash.

If a conditional put fails, retry from the latest object bytes and ETag.

S3 atomic object replacement can leave the prior object visible on interruption. Immutable batch objects plus `manifest.json` are the source of truth. Resume may reconstruct missing observability events in `progress.jsonl` or `errors.jsonl` from batch and manifest state.

`manifest.json`, `watcher.json`, and `active_openai_batch.json` also use conditional atomic whole-object replacement with `If-Match` ETag for concurrency control.

## Deterministic run id and immutability

Per-feature run id (stored in every row as `run_id`):

`bluesky_2026_09_03_235130_llm_features_v1:{feature}`

Restart and resume reuse the same `run_id` and the same feature prefix. Feature prefixes are immutable except:

- Logical append to `progress.jsonl` and `errors.jsonl`.
- Conditional atomic replacement of `manifest.json`, `watcher.json`, and `active_openai_batch.json`.
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

## Row schema (Q44)

Every row in `smoke/output.parquet`, `batches/part-*.parquet`, and `final.parquet` must contain exactly these columns:

| Column | Meaning |
|--------|---------|
| `source_record_id` | Pinned preprocessed post id |
| `run_id` | `bluesky_2026_09_03_235130_llm_features_v1:{feature}` |
| `batch_id` | OpenAI Batch provider id for the batch that produced the row |
| `request_id` | Provider request id for the row |
| `attempt_count` | Integer attempt count for this row (1 through 4) |
| `label_timestamp` | UTC timestamp from `lib.timestamp_utils.get_current_timestamp` |
| `{label_field}` | That feature's raw label column from the table above |

Validation applies the feature Pydantic model to the label-field subset and separately validates provenance columns.

## Campaign CLI

Extend existing `data_platform/generate_features/generate_bluesky_features.py` with `--campaign-id` and `--preprocessed-run` for production campaign mode. Keep legacy mode when those flags are absent.

Campaign mode rules:

- Pass exactly one value to `--features`.
- Pass `--batch-size 2000`.
- Campaign mode automatically resumes feature state in its canonical prefix on restart.
- Do not add `run_bluesky_llm_campaign.py`, `--resume`, `APPROVED.txt`, or a timestamp `--checkpoint`.

Example campaign command:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

The blocking engine stays. At most one OpenAI Batch job is active per feature at a time.

## Smoke tooling and approval flow (Step 6)

Step 6 adds reusable tooling only:

- `data_platform/generate_features/smoke_bluesky_campaign.py`
- An aggregation command that sums seven per-feature cost estimates

Step 6 does not run full 200k labeling and does not add a file-based approval marker.

Deterministic ten-post sample (shared by all seven features):

1. Load pinned preprocessed run `2026_09_03-23:51:30`.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

Steps 8 through 14 (each in its own feature PR):

1. Run `smoke_bluesky_campaign.py` once for that feature (includes deliberate interruption and resume).
2. Commit temporary Git smoke evidence under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/{feature}/`.
3. Post the estimated full-run cost to that feature's GitHub issue.
4. Pause until all seven feature issues have estimates and the parent campaign issue has one aggregate estimate plus explicit human approval.

Human approval is recorded on the parent GitHub issue only. No `APPROVED.txt` or other repository approval file.

## Progress and watcher (Step 7)

`progress.jsonl` is the only progress event file. Each append records durable row totals and batch metadata after a canonical batch lands.

`watcher.json` stores:

- `github_comment_id` (rolling feature-issue comment)
- `last_posted_milestone` (last 10k boundary posted: 10000, 20000, …, 200000)

The watcher CLI prints a prepared markdown report. A restartable agent outside repository code posts or updates one feature-issue comment through authenticated GitHub integration. Repository code must not launch Cursor and must not call GitHub write APIs directly.

## Permanent report paths

| Report | Path |
|--------|------|
| Per-feature | `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/{feature}_run_report.md` |
| Wide consolidation | `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md` |

Temporary Git smoke evidence (committed during Phase A, deleted before merge):

`docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/{feature}/`

## Wide table (Step 15)

Wide output: exactly nineteen columns.

Twelve preprocessed columns (exact names):

`uri`, `record_id`, `url`, `author_handle`, `text`, `created_at`, `like_count`, `repost_count`, `reply_count`, `quote_count`, `sync_timestamp`, `source_record_id`

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

Wide manifest links all seven per-feature provenance manifests plus preprocessed input hash.

Forbidden wide columns: `toxicity_tier`, `toxicity_prob`, `label_timestamp`, `run_id`, any Perspective column.

## Step dependencies

| Step | Depends on | Can run parallel with | Delivers |
|------|------------|----------------------|----------|
| 1 | none | 2, 4 | S3 copy of pinned Bluesky pipeline and dump trees |
| 2 | none | 1, 4 | Configurable S3 object store |
| 3 | 1, 2 | none (after 1 and 2) | S3 default backend; remove Bluesky pipeline LFS pointers |
| 4 | none | 1, 2 | OpenAI Batch resume and partial-success engine |
| 5 | 2, 4 | none (after 2 and 4) | Campaign S3 layout, Q44 rows, `active_openai_batch.json`, batch tagging, append semantics |
| 6 | 5 | 7 | Smoke tooling and cost aggregation |
| 7 | 5 | 6 | Progress enrichment and watcher CLI |
| 8 through 14 | 3, 6, 7 (transitively 2, 4, 5) | each other | One feature run each (docs-only PRs) |
| 15 | 8 through 14 | none | Wide join |
| 16 | 5 tagging only | listed last | 30-day lifecycle on tagged batch objects |

Step 16 is last in the schedule. Its only technical prerequisite is Step 5 intermediate tagging, not Step 15.

Feature Steps 8 through 14 require Step 3 (production S3 backend), Step 6 (smoke tooling), and Step 7 (watcher). They transitively rely on Steps 2, 4, and 5 through those dependencies.

## Verification rules

- Content hashes are SHA-256 lowercase hex of full object bytes. Never accept S3 ETag as a content hash.
- S3 ETag with `If-Match` is permitted only for concurrency control on conditional replace of `progress.jsonl`, `errors.jsonl`, `manifest.json`, `watcher.json`, and `active_openai_batch.json`.
- No automated tests are added or run for this epic. Use live smoke and basic runtime checks only.
- Temporary Git smoke files may be committed during review and must be removed before merge.

## Hash and manifest rules

`manifest.json` at each feature prefix and `wide/manifest.json` use SHA-256 hex digests only. Do not use MD5, ETag alone, or size-only checks as acceptance gates.
