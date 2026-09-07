# Step 2: Smoke and generate seven LLM features for 6,374 Twitter posts

## Goal

One pull request runs the seven ten-post smokes, posts cost on the parent issue, waits for owner sign-off, then labels all 6,374 posts on OpenAI Batch with `gpt-5.4-nano`, one feature at a time. The pull request carries documentation and run artifacts only. It does not change product code.

## Dependencies

- **Step 1 merged** on the GitHub stack: csv on S3, campaign YAML, `generate_twitter_features.py` campaign mode, `smoke_twitter_campaign.py`, cost aggregate with `--full-run-row-count 6374`, watcher flags.
- **Parent issue owner sign-off** after Phase A, before Phase B. Sign-off is a comment on the parent issue. It is not a GitHub `blocked-by`. Merged Step 1 is not permission to label 6,374 rows.

Pinned identities: see `campaign_contract.md`.

## Main caller and implementation scope

Phase A (each feature, YAML order). Interrupt and resume only on `is_news_or_opinion`:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_news_or_opinion
```

Repeat for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tiered` without a second interrupt.

Aggregate after all seven cost reports exist:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --smoke-reports-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke \
  --output docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/parent_cost_aggregate.json \
  --full-run-row-count 6374
```

Phase B (each feature, same order, after parent sign-off):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

**One implementation scope:** run the callers above. Commit temporary smoke Git copies in Phase A. Post per-feature costs on this issue and the aggregate on the parent. Stop. After the owner comments on the parent, run production serially, write seven run reports, delete temporary smoke Git copies. Do not edit Python under `data_platform/` or `lib/`.

**Out of scope:** product-code changes, pytest, GitHub posting from repository code, wide join, changing filter YAML, Bedrock, Perspective `is_toxic_tiered`, parallel OpenAI Batch jobs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md` | Identities, part layout, schemas |
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md` | Tooling that must already be on the stack |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` | Feature order and row count |
| `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` | Phase A caller |
| `/workspace/data_platform/generate_features/generate_twitter_features.py` | Phase B caller |
| `/workspace/data_platform/generate_features/generate_features.py` | `_smoke_rows_by_id` fold |

## Files allowed to change

- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/**` (temporary Phase A copies, deleted before merge)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_news_or_opinion_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_political_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_likely_spam_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_self_contained_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_structurally_complete_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/political_stance_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/llm_toxicity_tiered_run_report.md` (new, keep)
- `/workspace/CHANGELOG.md`

Do not edit this step file except to correct a spec bug.

## Files forbidden to change

- Any file under `/workspace/data_platform/` except the reports and changelog listed above
- `/workspace/lib/`
- `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`
- Any committed parquet or csv label file

## Locked contracts

Serial feature order:

1. `is_news_or_opinion` (interrupt-and-resume once during its smoke)
2. `is_political`
3. `is_likely_spam`
4. `is_self_contained`
5. `is_structurally_complete`
6. `political_stance`
7. `llm_toxicity_tiered`

After parent approval, each feature must have:

- `smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json` (untagged)
- `smoke/resume_evidence.json` on `is_news_or_opinion` only
- `batches/part-00000.parquet` (10 smoke rows + 1,990 new)
- `batches/part-00001.parquet` (2,000)
- `batches/part-00002.parquet` (2,000)
- `batches/part-00003.parquet` (374)
- `final.parquet` with 6,374 unique `source_record_id` values
- `manifest.json` with `engine_type=openai` and `expected_row_count=6374`
- `progress.jsonl` with one record per finished part

Preserve original smoke `batch_id` and `request_id` on the ten folded rows. One OpenAI Batch job in flight per feature. Do not start the next feature's production command until the previous feature's `final.parquet` validates.

## Two-phase pull request flow

### Phase A

1. Confirm Step 1 is on the stack below this branch.
2. Run `smoke_twitter_campaign.py` for all seven features. Interrupt and resume only `is_news_or_opinion`.
3. Commit temporary Git copies under `reports/smoke/{feature}/`.
4. Post each per-feature `estimated_full_run_usd_avg` and `estimated_full_run_usd_max` on this issue.
5. Write and post `parent_cost_aggregate.json` on the parent issue.
6. Stop. Leave the stack pull request as draft. Do not start production.

### Phase B

1. Confirm the parent issue has an explicit owner comment signing off on Step 1, the seven smokes, and the aggregate cost.
2. Run the seven production commands in order.
3. Validate S3 artifacts and row counts for each feature before starting the next.
4. Write the seven `*_run_report.md` files.
5. Delete temporary `reports/smoke/` Git copies. S3 smoke evidence remains.
6. Mark the stack pull request ready.

## Exact commands and expected output

List one feature prefix:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/ --recursive
```

Expected after Phase A: smoke objects only. No `batches/part-*.parquet`.

Expected after Phase B: four `batches/part-*.parquet` objects, `final.parquet`, `manifest.json`, `progress.jsonl`.

Validate one final file:

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/final.parquet /tmp/twitter_is_news_or_opinion_final.parquet
PYTHONPATH=. uv run python - <<'PY'
import pyarrow.parquet as pq
t = pq.read_table("/tmp/twitter_is_news_or_opinion_final.parquet")
assert t.num_rows == 6374, t.num_rows
ids = t.column("source_record_id").to_pylist()
assert len(set(ids)) == 6374
print("final ok", t.num_rows)
PY
```

Expected: `final ok 6374`.

Watcher (no GitHub post):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --feature is_news_or_opinion \
  --platform twitter \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --once
```

Expected: printed markdown. 10,000-row milestone absent.

Each run report must include S3 URIs, manifest SHA-256, model id `gpt-5.4-nano`, prompt hash, estimated and actual USD, part counts, unique id count 6374, and a note that Git smoke copies were removed.

## Acceptance criteria

- Seven smoke cost estimates are posted on this issue. Aggregate is posted on the parent.
- Parent issue has explicit owner sign-off before any `batches/part-*.parquet` object exists.
- Each feature has four batch objects and `final.parquet` with 6,374 unique ids.
- Only `is_news_or_opinion` has `resume_evidence.json`.
- Seven run reports remain in Git. Temporary smoke Git copies are gone.
- No product-code diff.

## Failure conditions

- Phase B starts without a parent-issue owner comment.
- Two OpenAI Batch jobs for the same feature exist at once.
- Smoke rows in `part-00000` have new `batch_id` values.
- `part-00003` does not have 374 rows.
- Perspective `is_toxic_tiered` runs.
- Product Python changes.
- Pytest added or run.
- Watcher posts to GitHub.

## PR artifact and commit rules

- One independently mergeable PR for this step only, stacked on Step 1.
- Stay draft through Phase A. Ready after Phase B.
- PR title suggestion: `Label 6374 Twitter posts with seven OpenAI LLM features`.

## GitHub issue body

Generate all seven LLM features for 6,374 pinned Twitter posts through OpenAI Batch with model `gpt-5.4-nano` in one pull request. Run Phase A smoke once per feature with `smoke_twitter_campaign.py`, interrupt and resume only `is_news_or_opinion`, post costs, and wait for parent issue owner sign-off before Phase B. Phase B writes four immutable batch objects, `final.parquet`, `manifest.json`, progress records, and a permanent run report per feature on S3. The pull request carries documentation and run artifacts only and does not change product code.

Plan step: `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`

Done when:

- Seven smoke cost estimates and the parent aggregate are posted.
- Parent issue has explicit owner sign-off before the 6,374-post runs start.
- S3 holds four batch objects and validated `final.parquet` with 6374 unique `source_record_id` values per feature.
- Seven `reports/*_run_report.md` files are committed and temporary Git smoke copies are removed before merge.

Ship as one PR. Do not bundle with sibling issues.

## Pull request description

# Label 6374 Twitter posts with seven OpenAI LLM features

Fixes #<child>

Part of #<parent>

## Problem

The dated Twitter collection is labeled only after smoke costs are reviewed. Operators need all seven features in one stack pull request, with a pause for parent-issue sign-off.

## Solution

Phase A runs `smoke_twitter_campaign.py` for seven features and posts `parent_cost_aggregate.json` scaled to 6,374 rows. After owner sign-off, Phase B runs `generate_twitter_features.py` once per feature with `--batch-size 2000`. No product code.

## How to run

See the Phase A and Phase B command blocks in the step file.

Expected after Phase B: seven `final.parquet` files, each with 6,374 rows, and seven run reports in git.
