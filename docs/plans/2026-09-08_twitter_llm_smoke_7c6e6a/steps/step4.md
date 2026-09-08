# Step 4: Label 6408 posts after parent owner sign-off

## Scope

- **Caller:** `data_platform/generate_features/generate_twitter_features.py` `main`.
- **Task:** After an owner comment on issue 251 signs off on Step 3, the seven smokes, and the aggregate cost, label all 6,408 posts for each feature in YAML order with OpenAI Batch model `gpt-5.4-nano` and `--batch-size 2000`.
- **Out of scope:** Starting production in the Phase A round. Product Python. Pytest. Parallel OpenAI Batch jobs. Perspective `is_toxic_tiered`. Bedrock. Wide join.

Phase B waits for that owner comment. Do not run this step in the Phase A round.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml`

## Files allowed to change

None in Git during the production commands. S3 objects under the campaign feature prefixes are the runtime output.

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any committed parquet or csv label file

## Gate

Stop unless issue 251 has an explicit owner comment that signs off on Step 3, the seven smokes, and the aggregate cost. Merged child #254 is not that comment.

## Work

Run one feature at a time. Do not start the next feature until the previous feature's `final.parquet` validates with 6,408 unique `source_record_id` values.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export PYTHONPATH=.

PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08 \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

Repeat for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, and `llm_toxicity_tiered`.

After each feature, list the prefix and validate `final.parquet`:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_news_or_opinion/ --recursive
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_news_or_opinion/final.parquet /tmp/twitter_is_news_or_opinion_final.parquet
PYTHONPATH=. uv run python - <<'PY'
import pyarrow.parquet as pq
t = pq.read_table("/tmp/twitter_is_news_or_opinion_final.parquet")
assert t.num_rows == 6408, t.num_rows
ids = t.column("source_record_id").to_pylist()
assert len(set(ids)) == 6408
print("final ok", t.num_rows)
PY
```

Expected: `final ok 6408`. Four `batches/part-*.parquet` objects, `final.parquet`, `manifest.json`, and `progress.jsonl`. Smoke objects remain. Only `is_news_or_opinion` has `smoke/resume_evidence.json`. Last part size is 1408 when remainder is not 0 (`6408 % 2000`).

Preserve original smoke `batch_id` and `request_id` on the ten folded rows in `part-00000`. One OpenAI Batch job in flight per feature.

Optional watcher during or after a production feature, `--once` only:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --once \
  --platform twitter \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --feature is_news_or_opinion
```

Expected: prepared markdown printed, `github_write_skipped=true`, no GitHub post.

## Pass

- Parent owner comment exists before the first production command.
- Each feature has four batch objects and a validated `final.parquet` with 6,408 unique ids.
- `part-00003` has 1408 rows.

## Fail

- Production starts before the parent owner comment.
- `--full-run-row-count 6374` is used.
- More than one OpenAI Batch job runs at a time for a feature.
- Smoke rows are relabeled into `part-00000`.
- Product Python changes.
