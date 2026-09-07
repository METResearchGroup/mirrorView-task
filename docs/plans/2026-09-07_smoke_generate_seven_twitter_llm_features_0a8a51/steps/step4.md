# Step 4: Label 6374 posts after parent owner sign-off

## Scope

- **Caller:** `data_platform/generate_features/generate_twitter_features.py` `main`.
- **Task:** After an owner comment on issue 232 signs off on Step 1, the seven smokes, and the aggregate cost, label all 6,374 posts for each feature in YAML order with OpenAI Batch model `gpt-5.4-nano` and `--batch-size 2000`.
- **Out of scope:** Starting production in the Phase A round. Product Python. Pytest. Parallel OpenAI Batch jobs. Perspective `is_toxic_tiered`. Bedrock. Wide join.

Phase B waits for that owner comment. Do not run this step in the Phase A round.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`

## Files allowed to change

None in Git during the production commands. S3 objects under the campaign feature prefixes are the runtime output.

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`
- Any committed parquet or csv label file

## Gate

Stop unless issue 232 has an explicit owner comment that signs off on Step 1, the seven smokes, and the aggregate cost. Merged or open Step 1 is not that comment.

## Work

Run one feature at a time. Do not start the next feature until the previous feature's `final.parquet` validates with 6,374 unique `source_record_id` values.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

Repeat for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, and `llm_toxicity_tiered`.

After each feature, list the prefix and validate `final.parquet`:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/ --recursive
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

Expected: `final ok 6374`. Four `batches/part-*.parquet` objects, `final.parquet`, `manifest.json`, and `progress.jsonl`. Smoke objects remain. Only `is_news_or_opinion` has `smoke/resume_evidence.json`.

Preserve original smoke `batch_id` and `request_id` on the ten folded rows in `part-00000`. One OpenAI Batch job in flight per feature.

## Pass

- Parent owner comment exists before the first production command.
- Each feature has four batch objects and a validated `final.parquet` with 6,374 unique ids.
- `part-00003` has 374 rows.

## Fail

- Production runs in the Phase A round.
- Two OpenAI Batch jobs for the same feature exist at once.
- Smoke rows in `part-00000` have new `batch_id` values.
- Perspective `is_toxic_tiered` runs.
- Product Python changes.
