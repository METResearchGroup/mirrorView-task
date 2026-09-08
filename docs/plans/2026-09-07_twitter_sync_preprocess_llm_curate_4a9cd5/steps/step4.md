# Step 4: Smoke and generate seven LLM features for the new Twitter posts

## Goal

One pull request runs the seven ten-post smokes, posts cost on the parent issue, waits for owner sign-off, then labels every preprocessed row on OpenAI Batch with `gpt-5.4-nano`, one feature at a time. The pull request carries documentation and run artifacts only. It does not change product code.

## Dependencies

- **Step 3 merged** on the GitHub stack: csv on S3, new campaign YAML, directory loader, migrate/verify flags.
- **Parent issue owner sign-off** after Phase A, before Phase B. Sign-off is a comment on the parent issue. It is not a GitHub `blocked-by`. Merged Step 3 is not permission to label the full preprocessed set.

Pinned identities: see `campaign_contract.md`. Replace `{campaign_id}`, `{preprocessed_run}`, and `{row_count}` from Step 2 / Step 3 YAML.

## Caller / unit of work

Phase A (each feature, YAML order). Interrupt and resume only on `is_news_or_opinion`:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id {campaign_id} \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/is_news_or_opinion
```

Repeat for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tiered` without a second interrupt.

Aggregate after all seven cost reports exist:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id {campaign_id} \
  --smoke-reports-dir docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke \
  --output docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/parent_cost_aggregate.json \
  --full-run-row-count {row_count}
```

Phase B (each feature, same order, after parent sign-off):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --campaign-id {campaign_id} \
  --features is_news_or_opinion \
  --batch-size 2000
```

Watcher during or after a production feature (optional, `--once` only):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --once \
  --platform twitter \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --campaign-id {campaign_id} \
  --feature is_news_or_opinion
```

Expected: prepared markdown printed, `github_write_skipped=true`, no GitHub post.

**One implementation scope:** run the callers above. Commit temporary smoke Git copies in Phase A. Post per-feature costs on this issue and the aggregate on the parent. Stop. After the owner comments on the parent, run production serially, write seven run reports, delete temporary smoke Git copies. Do not edit Python under `data_platform/` or `lib/`.

**Out of scope:** product-code changes, pytest, GitHub posting from repository code, wide join, changing filter YAML, Bedrock, Perspective `is_toxic_tiered`, parallel OpenAI Batch jobs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/campaign_contract.md` | Identities, part layout, schemas |
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step3.md` | Tooling that must already be on the stack |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml` | Feature order and row count |
| `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` | Phase A caller |
| `/workspace/data_platform/generate_features/generate_twitter_features.py` | Phase B caller |
| `/workspace/data_platform/generate_features/generate_features.py` | `_smoke_rows_by_id` fold |

## Files allowed to change

- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/**` (temporary Phase A copies, deleted before merge)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/is_news_or_opinion_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/is_political_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/is_likely_spam_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/is_self_contained_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/is_structurally_complete_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/political_stance_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/llm_toxicity_tiered_run_report.md` (new, keep)
- `/workspace/CHANGELOG.md`

Do not edit this step file except to correct a spec bug. Do not edit `plan.md` or `campaign_contract.md` during implementation except to fill Step 2 identities if they were still placeholders.

## Files forbidden to change

- Any file under `/workspace/data_platform/` except changelog listed above
- `/workspace/lib/`
- `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
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

`resume_evidence.json` is required on `is_news_or_opinion` only. The other six features must not write it.

After parent approval, each feature must have:

- `smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json` (untagged)
- `smoke/resume_evidence.json` on `is_news_or_opinion` only
- `batches/part-00000.parquet` (10 smoke rows + up to 1,990 new)
- later `batches/part-*.parquet` objects covering the remaining rows
- last part size `row_count % 2000` when that remainder is not 0
- `final.parquet` with `{row_count}` unique `source_record_id` values
- `manifest.json` with `engine_type=openai` and `expected_row_count={row_count}`
- `progress.jsonl` with one record per finished part

Preserve original smoke `batch_id` and `request_id` on the ten folded rows. One OpenAI Batch job in flight per feature. Do not start the next feature's production command until the previous feature's `final.parquet` validates.

Do not use `--full-run-row-count 6374`.

## Two-phase pull request flow

### Phase A

1. Confirm Step 3 is on the stack below this branch.
2. Run `smoke_twitter_campaign.py` for all seven features. Interrupt and resume only `is_news_or_opinion`.
3. Commit temporary Git copies under `reports/smoke/{feature}/`.
4. Post each per-feature `estimated_full_run_usd_avg` and `estimated_full_run_usd_max` on this issue.
5. Write and post `parent_cost_aggregate.json` on the parent issue.
6. Stop. Leave the stack pull request as draft. Do not start production.

### Phase B

1. Confirm the parent issue has an explicit owner comment signing off on Step 3, the seven smokes, and the aggregate cost.
2. Run the seven production commands in order.
3. Validate S3 artifacts and row counts for each feature before starting the next.
4. Write the seven `*_run_report.md` files.
5. Delete temporary `reports/smoke/` Git copies. S3 smoke evidence remains.
6. Mark the stack pull request ready.

## Exact commands and expected output

List one feature prefix:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/{campaign_id}/is_news_or_opinion/ --recursive
```

Expected after Phase A: smoke objects only. No `batches/part-*.parquet`.

Expected after Phase B: `batches/part-*.parquet` objects covering `{row_count}` rows, `final.parquet`, `manifest.json`, `progress.jsonl`.

Phase A smoke stdout for `is_news_or_opinion` includes `s3_smoke_resume_evidence_ok`. The other six features include `resume_evidence_absent`.

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
p = Path("docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/parent_cost_aggregate.json")
doc = json.loads(p.read_text())
print(doc.get("full_run_row_count") or doc.get("row_count"))
print(doc.get("estimated_full_run_usd_avg"))
print(doc.get("estimated_full_run_usd_max"))
PY
```

Expected: printed full-run row count equals campaign YAML `row_count`, plus average and max USD estimates.

Do not add pytest.

## Pass / fail

The step passes when seven smokes and the aggregate cost are posted on the parent, the owner signs off in a comment, each feature `final.parquet` has `{row_count}` unique valid labels, smoke rows keep original ids inside `part-00000`, resume evidence exists only for `is_news_or_opinion`, seven run reports are committed, and temporary Git smoke copies are gone.

The step fails when any item below is true.

- product Python changed
- production started before the parent owner comment
- `--full-run-row-count 6374` was used
- `resume_evidence.json` was written for a feature other than `is_news_or_opinion`
- smoke rows were relabeled into `part-00000`
- more than one OpenAI Batch job ran at a time for a feature
- pytest was added

## PR artifact and commit rules

- One independently mergeable PR stacked on Step 3. Phase A and Phase B share that PR.
- Logical commits: Phase A smoke copies, Phase B run reports, changelog if used, deletion of smoke copies.
- PR title suggestion: `Smoke and generate seven LLM features for the new Twitter posts`.
