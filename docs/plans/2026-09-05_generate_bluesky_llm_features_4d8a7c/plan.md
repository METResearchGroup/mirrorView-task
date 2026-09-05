# Generate seven reliable S3-backed LLM features for 200,000 Bluesky posts

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY and YAGNI
- Use only the approved smoke checks. Do not add or run automated tests.
- Frequent commits
- Delegated tasks must be impossible to misread.

## Overview

Move the current pipeline data from Git LFS to the `mirrorview-experimental-artifacts` S3 bucket, and make S3 the production storage backend while retaining local storage for development. Harden the OpenAI Batch feature generator, then generate seven LLM features for the pinned 200,000-post Bluesky dataset from PR #164.

Each feature run writes 100 immutable 2,000-row Parquet batch objects, a final feature Parquet file, a hash manifest, progress records, and a permanent run report. A final step joins the seven outputs with the complete preprocessed post records.

## Happy flow

An operator starts seven feature agents after the storage, reliability, smoke tooling, and watcher work has merged. Each agent runs the same ten-post smoke sample once through `smoke_bluesky_campaign.py` and posts its cost estimate to its feature issue. The parent issue records the total estimate and waits for one approval before the agents process the remaining posts.

```mermaid
flowchart TD
    A[Step1 Copy pipeline LFS to S3]
    B[Step2 Add S3 storage support]
    D[Step4 Harden OpenAI Batch resume]
    A --> C[Step3 S3 default backend]
    B --> C
    B --> E[Step5 Campaign S3 batches]
    D --> E
    E --> F[Step6 Smoke tooling]
    E --> G[Step7 Progress watcher]
    C --> H[Steps8-14 Feature runs]
    F --> H
    G --> H
    H --> J[Step15 Wide join]
    E --> K[Step16 Lifecycle rule]
```

## Approach

Use the fixed dataset `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` and preprocessed run `2026_09_03-23:51:30`. Record the input hash so a later dataset requires a separate campaign.

Store pipeline artifacts under `s3://mirrorview-experimental-artifacts/data_platform/data/`. Use one campaign ID and one isolated prefix per feature so parallel agents cannot change the same metadata. Keep one blocking OpenAI Batch job per feature agent, persist provider job IDs in `active_openai_batch.json` before polling, and resume the existing provider job after an interruption.

Smoke writes untagged evidence under `{feature}/smoke/` and never writes canonical `batches/part-*.parquet`. After parent approval, the first production provider job labels 1,990 new posts; those rows are combined with the ten unchanged smoke output rows into `part-00000.parquet`. The next 99 provider jobs each label 2,000 posts.

Each feature issue is one future pull request. Temporary Git smoke inputs, outputs, cost records, and resume evidence are committed for review and removed before merge. S3 smoke evidence under `{feature}/smoke/` remains. The permanent run report records the S3 locations, hashes, model and prompt identity, costs, throughput, retries, validation checks, and label counts.

See `campaign_contract.md` for the full dependency graph, S3 layout, and schemas.

## Decisions

- Canonical identities, S3 layout, schemas, and the dependency graph live in `campaign_contract.md`.
- Each feature pull request runs one canonical smoke, then waits for aggregate parent-issue cost approval before the full 200,000-post run.
- Human approval is recorded on the parent GitHub issue only. No repository approval file.
- Do not add or run automated tests. Use only the approved smoke and basic runtime checks defined in the step specs.

## Steps

### Step 1: Copy current pipeline LFS artifacts to S3

Copy the current pipeline data and required source dumps to matching S3 keys. Verify every object with SHA-256 hashes, retain the Git LFS copies, and commit the migration inventory. No dependencies. May run in parallel with Steps 2 and 4.

### Step 2: Add first-class S3 storage support to the data pipeline

Add configurable S3 reads and writes while preserving local storage for development. Reject Git LFS pointer text, unsafe paths, missing hashes, and accidental overwrites. No dependencies. May run in parallel with Steps 1 and 4.

### Step 3: Make S3 the default pipeline backend and remove current LFS artifacts

Set S3 as the production backend after the copied objects and S3 reader have been verified. Remove current pipeline artifacts from Git LFS without rewriting repository history. Depends on Steps 1 and 2.

### Step 4: Harden OpenAI Batch feature generation and resume

Persist in-flight OpenAI job identity, keep successful records from partly failed jobs, retry only transient failures, and make every run resumable. Define `active_openai_batch.json` state contract independent of storage. Mark a feature complete only after every pinned input ID has one valid output. No dependencies. May run in parallel with Steps 1 and 2.

### Step 5: Write resumable 2,000-row Parquet feature batches

Write immutable S3 batches, `active_openai_batch.json`, logical-append progress and error records, hash manifests, and one final Parquet file per feature. Keep one provider job active per feature and preserve deterministic record order during resume and consolidation. Depends on Steps 2 and 4.

### Step 6: Add smoke tooling and cost aggregation

Use one deterministic ten-post sample for every feature. Write untagged smoke evidence to `{feature}/smoke/`. Record average and maximum token usage, current model pricing, estimated full-run cost, S3 checks, and one deliberate interruption and resume inside the smoke caller. Depends on Step 5. May run in parallel with Step 7.

### Step 7: Add durable progress reports for feature run watchers

Write structured progress records after each durable batch. Give short, restartable watcher subagents enough information to update one rolling GitHub issue comment at every 10,000 completed records. Depends on Step 5. May run in parallel with Step 6.

### Step 8: Generate is_news_or_opinion for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `is_news_or_opinion`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 9: Generate is_political for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `is_political`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 10: Generate is_likely_spam for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `is_likely_spam`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 11: Generate is_self_contained for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `is_self_contained`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 12: Generate is_structurally_complete for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `is_structurally_complete`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 13: Generate political_stance for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `political_stance`. Publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 14: Generate llm_toxicity_tiered for 200,000 Bluesky posts

Run the approved smoke and full generation flow for `llm_toxicity_tiered`. Keep its output distinct from the Perspective API toxicity feature, and publish its final Parquet file, manifest, progress history, validation results, and permanent run report. Depends on Steps 3, 6, and 7.

### Step 15: Consolidate seven Bluesky LLM features into one wide Parquet artifact

Join the seven verified feature outputs to all 12 preprocessed post columns by `source_record_id`. Require exactly 200,000 unique records with no missing feature values, and publish the wide artifact, hash manifest, validation results, and permanent report. Depends on Steps 8 through 14.

### Step 16: Expire intermediate data platform S3 batches after 30 days

Add an S3 lifecycle rule that combines the `data_platform/data/` prefix with an intermediate-artifact tag. Expire only tagged batch objects and retain final Parquet files, manifests, progress records, and reports. Depends on Step 5 tagging only. Listed last in the schedule.

## What "done" looks like

1. The current pipeline data is available from S3 with verified hashes, and production pipeline runs no longer depend on current Git LFS artifacts.
2. Interrupted OpenAI Batch work resumes without duplicate provider jobs or duplicate charges.
3. Seven feature issues each produce exactly 200,000 unique, valid LLM labels across 100 canonical batch objects and one permanent run report.
4. Each issue reports progress every 10,000 durable records and records estimated and actual cost.
5. One wide Parquet artifact contains the 12 pinned post columns and all seven LLM feature outputs.
6. Intermediate batches expire after 30 days, while final artifacts and audit records remain in S3.
