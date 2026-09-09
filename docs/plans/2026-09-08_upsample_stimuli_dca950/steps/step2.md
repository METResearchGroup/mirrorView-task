# Step 2: Promote 300 leftover right-medium posts to high and write the unified upsample

## Scope

- **Caller:** `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py` `main`
- **Task:** After Step 1, take the rest of the cleaned medium posts, keep right-leaning rows that are not in pull request 260, score them with the Perspective thread-pool engine, reclassify the top 300 as high, write the 300 row parquet, concatenate it with the 2,000 medium upsample, and upload the unified 2,300 post parquet.
- **Out of scope:** pytest, Bedrock, the catalog, remaining labels, editing pull request 260 files, editing the 2,000 medium S3 object, scoring left-medium leftover, scoring low or high posts.

## Dependencies

Step 1 has uploaded `upsample_2000_medium_toxicity_posts.parquet` and committed its SHA-256 in `experiments/upsample_medium_toxicity_posts_2026_09_08/RESULTS.md`. Pin that SHA-256 in this experiment before scoring. Expected row count is 2000.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_upsample_stimuli_dca950/plan.md` | Candidate rule, 300 promotions, unified 2300 |
| `/workspace/docs/plans/2026-09-08_upsample_stimuli_dca950/steps/step1.md` | Cleanup and leftover medium contract |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/score_medium.py` | Perspective engine, batch 64, concurrency 80, resume scores |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/promote_v2.py` | Rank by `toxicity_prob` descending, id ascending, take top N |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/outputs/promotion_source_record_ids.json` | 3000 pull request 260 ids |
| `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/README.md` | `GOOGLE_API_KEY` through `EnvVarsContainer` |
| `/workspace/data_platform/generate_features/registry.py` | `FEATURE_REGISTRY["is_toxic_tiered"]` |
| `/workspace/ml_tooling/perspective_api.py` | Do not call directly. Do not edit. |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/README.md` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/sources.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/candidates.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/score.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/promote.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/write.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py` (new)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore cache, local parquet, and scores under this folder)
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/outputs/promotion_record_ids.json` after the live run
- `/workspace/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/RESULTS.md` after the live run
- `/workspace/CHANGELOG.md` after the unified S3 object exists

## Files forbidden to change

- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/**`
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/README.md`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/is_toxic_tiered/**`
- `/workspace/ml_tooling/perspective_api.py`
- `/workspace/tests/**`
- The 2,000 medium S3 object
- The 10,200 sample S3 object
- `mirrorview.parquet` and `mirrorview_v2.parquet`

## README contract

Write `README.md` first. Start with the same agent read-only banner as the filter-posts README. After it is committed, later steps must not edit it.

The README must say: take the 2,000 medium upsample first, then the rest of the cleaned medium posts, keep right-leaning rows, drop pull request 260 ids, score with Perspective, promote the top 300 to high, and write the unified 2,300 post table. Name `GOOGLE_API_KEY`. Include the run command.

## Candidate contract

Rebuild the cleaned table the same way as Step 1. Drop `record_id` values that are in the 10,200 sample. Drop `record_id` values that are in the 2,000 medium upsample. Keep `llm_toxicity_tier == "medium"`. Keep `political_stance == "right"`. Drop rows whose `source_record_id` is in the 3,000 id JSON from pull request 260.

Expected leftover right-medium after dropping the 2,000 is 2,865. Pull request 260 overlap in that leftover should be 0. Print `pr260_ids_dropped=`. If remaining candidates are fewer than 300, raise `ValueError`.

Do not include left-medium leftover. Do not include posts from the 10,200 sample. Do not include posts from the 2,000 medium upsample.

## Scoring contract

Copy the Perspective scoring pattern from `experiments/reddit_curated_perspective_v2_2026_09_08/score_medium.py`. Do not import that module, because it uses `source_record_id` as the task id. Use `record_id` as `LabelTask.uri` and `text` as `LabelTask.text`.

Build the engine from `FEATURE_REGISTRY["is_toxic_tiered"]` with `FeatureRunConfig(max_concurrency=80, batch_size=64)`. Do not call `ml_tooling.perspective_api.get_toxicity_prob` except through that engine.

Save scores at `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/outputs/perspective_scores.parquet` with columns `record_id` and `toxicity_prob`. Skip ids that already have a finite probability in `[0, 1]`. Rewrite the scores file after each successful batch. Ignore Perspective `toxicity_tier` when ranking.

If any candidate still lacks a probability after the engine returns, raise `ValueError`. `GOOGLE_API_KEY` is required for the live run.

## Promotion contract

Rank scored candidates by `toxicity_prob` descending, then `record_id` ascending, `kind="mergesort"`. Take the first 300 ids. Copy those 300 rows from the candidate table. Set `llm_toxicity_tier` to `high`. Leave every other column unchanged. All 300 rows must have `political_stance == "right"`.

Concatenate the 2,000 medium upsample, toxicity still medium, with the 300 promoted rows. Fail if any `record_id` appears in both pieces. Sort by `integration`, `source_dataset_id`, `source_record_id` with `kind="mergesort"`. Reset the index.

Unified expected counts:

| Field | Value |
|-------|------:|
| Rows | 2300 |
| Medium | 2000 |
| High | 300 |
| Left | 1000 |
| Right | 1300 |
| Right high | 300 |
| Right medium | 1000 |
| Left medium | 1000 |

## Outputs

| Output | Path |
|--------|------|
| 300 row S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/upsample_300_right_high_toxicity_posts.parquet` |
| Unified S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/unified_upsampled_posts.parquet` |
| Promotion ids | `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/outputs/promotion_record_ids.json` |
| Report | `experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/RESULTS.md` |

Upload both parquets with `put_new`. A second upload of either key must fail.

`RESULTS.md` must include candidate count, `pr260_ids_dropped`, 300 promotions, unified stance by toxicity, both S3 URIs, and both SHA-256 values.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
```

Expected stdout includes `candidate_rows=` at least 300, `promotions=300`, `unified_rows=2300`, `unified_medium=2000`, `unified_high=300`.

A second run that already has complete scores and whose S3 keys exist must raise `FileExistsError` without calling Perspective again for ids that already have scores.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and GOOGLE_API_KEY is set
and Step 1 wrote the 2000 medium parquet
when PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
then candidate_rows is at least 300
and promotions=300
and every promoted row is right and high
and unified_rows=2300
and unified_medium=2000
and unified_high=300
and no unified record_id is in the 10200 sample
and no promoted record_id is in the 2000 medium parquet
and no promoted source_record_id is in the pull request 260 JSON
and both S3 objects exist
and RESULTS.md records those counts

given the unified S3 key already exists
when the command is run again
then the process raises FileExistsError
```

## Must pass

- Candidate construction drops the 10,200 sample, the 2,000 medium upsample, and pull request 260 ids.
- Scoring uses `FEATURE_REGISTRY["is_toxic_tiered"]` and `record_id` as the task id.
- Unified table is 2,300 rows, 2,000 medium and 300 right-high.
- Pull request 260 files and the 2,000 medium S3 object are unchanged.

## Must fail

- Fewer than 300 candidates.
- A promotion id that is left, or still medium after the copy.
- Hash mismatch on a pinned input.
- Second upload to either output key.
- Live Perspective calls in pytest. There is no pytest.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block in the `run.py` module docstring.

Phase 1 names `run.py` `main` as the caller: load, build candidates, score, promote, concatenate, write.

Phase 2 scaffolds stubs with that wiring.

Phase 3 locks signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. Pinned constants, including the Step 1 SHA-256
2. Candidate construction
3. Perspective score persist and resume
4. Top 300 promotion
5. Unified concatenate, `put_new`, `RESULTS.md`, `main`
6. README and `.gitignore`

Phase 6 is complete when the live command exits 0 and the unified S3 object exists. Leave the Perspective run going if it is still scoring. Do not start Step 3 until `unified_rows=2300`.
