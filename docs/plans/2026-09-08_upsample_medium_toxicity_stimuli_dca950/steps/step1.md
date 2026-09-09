# Step 1: Sample 2,000 unused medium toxicity posts

## Scope

- **Caller:** `experiments/upsample_medium_toxicity_posts_2026_09_08/run.py` `main`
- **Task:** Download the pinned combined parquet, run the same cleanup as pull request 267, drop ids from the 10,200 post sample, sample 1,000 leftover left-medium posts and 1,000 leftover right-medium posts with seed 42, write local parquet, upload to S3, print counts, write `README.md` and `RESULTS.md`.
- **Out of scope:** pytest, Perspective, Bedrock, the 300 right-high promotions, the catalog, remaining labels, editing the filter-posts README, overwriting the 10,200 post sample.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-08_upsample_medium_toxicity_stimuli_dca950/plan.md` | Confirmed decisions |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py` | Load, cleanup, sample, write caller |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/load_raw_candidate_dataset.py` | Download, hash check, cache, `CandidateSource` |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/cleanup_raw_candidate_dataset.py` | Previously used ids, original text, duplicate id, duplicate text |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/sources.py` | Combined columns, sort columns, stance and toxicity names |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/RESULTS.md` | 10,200 sample SHA-256 and sampled cell counts |
| `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/crosstab.py` | `stance_by_toxicity` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore.put_new` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/README.md` (new)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/sources.py` (new)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/sample_leftover_medium.py` (new)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/write.py` (new)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/run.py` (new)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/.gitignore` (new)
- `/workspace/.gitignore` (ignore cache and local parquet under this folder only)
- `/workspace/experiments/upsample_medium_toxicity_posts_2026_09_08/RESULTS.md` after the live run
- `/workspace/CHANGELOG.md` after the live S3 object exists

## Files forbidden to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/**` except do not add files there. Import load and cleanup. Do not edit the README.
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/**`
- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/**`
- `/workspace/shared/flip_generation/**`
- `/workspace/tests/**`
- The combined source S3 object
- The 10,200 sample S3 object

## README contract

Write `README.md` first. Start with the same agent read-only banner used in `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`. After it is committed, later steps must not edit it.

The README must name the 2,000 row target, the 1,000 left and 1,000 right split, seed 42, the combined source, the 10,200 sample, the output S3 URI, and the run command.

## Pinned inputs

| Field | Value |
|-------|-------|
| Combined object | `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet` |
| Combined SHA-256 | `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0` |
| Combined rows | 55573 |
| Sample object | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` |
| Sample SHA-256 | `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` |
| Sample rows | 10200 |

Reuse `load_raw_candidate_dataset` and `cleanup_raw_candidate_dataset` from the filter experiment. Pass a `CandidateSource` for each file. Use two cache directories under this experiment so the two parquets do not share one cache file.

## Sample contract

After cleanup, drop every row whose `record_id` is in the 10,200 sample. Then keep `llm_toxicity_tier == "medium"`.

Expected leftover after that drop:

| political_stance | leftover medium |
| ---------------- | --------------: |
| left | 15203 |
| right | 3865 |

Sample 1,000 left-medium rows and 1,000 right-medium rows with `random_state=42`, without replacement. If either leftover cell has fewer than 1,000 rows, raise `ValueError`. Concatenate, sort by `integration`, `source_dataset_id`, `source_record_id` with `kind="mergesort"`, and reset the index.

The output keeps the 17 combined columns in the same order. Every output `record_id` must be unique and must not appear in the 10,200 sample. Every output row must have `llm_toxicity_tier == "medium"`. Stance counts must be 1,000 left and 1,000 right.

## Outputs

| Output | Path |
|--------|------|
| Local parquet | `experiments/upsample_medium_toxicity_posts_2026_09_08/upsample_2000_medium_toxicity_posts.parquet` |
| S3 parquet | `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upsample_2000_medium_toxicity_posts.parquet` |
| Report | `experiments/upsample_medium_toxicity_posts_2026_09_08/RESULTS.md` |

Upload with `CampaignObjectStore.put_new`. A second upload of the same key must raise `FileExistsError`.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
```

Expected stdout includes `sampled_rows=2000`, `left_medium=1000`, `right_medium=1000`, `leftover_left_medium=15203`, `right_medium_leftover_before_sample=3865`, the S3 URI, and `dataset_sha256=`.

## Live given / when / then (Phase 4)

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned combined parquet exists at SHA-256 f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0
and the pinned 10200 sample exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
then sampled_rows=2000
and left_medium=1000
and right_medium=1000
and every output llm_toxicity_tier is medium
and no output record_id is in the 10200 sample
and S3 object experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upsample_2000_medium_toxicity_posts.parquet exists
and its SHA-256 matches the local file
and RESULTS.md records those counts

given the S3 upsample key already exists
when the command is run again
then the process raises FileExistsError and does not change the combined source or the 10200 sample
```

## Must pass

- Imports from `run.py` resolve.
- Combined and sample SHA-256 values and row counts are checked before sampling.
- Output has 2,000 rows, 1,000 left, 1,000 right, all medium.
- No overlap with the 10,200 sample.
- Filter-posts README is unchanged.

## Must fail

- Hash mismatch on either pinned parquet.
- Wrong pinned row count.
- Leftover left-medium or right-medium below 1,000.
- Second upload to the same S3 key.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block in the `run.py` module docstring.

Phase 1 names `run.py` `main` as the caller.

Phase 2 scaffolds `sources.py`, `sample_leftover_medium.py`, `write.py`, `run.py` with stub bodies and a thin `main`: load combined, cleanup, load sample, drop sample ids, sample leftover medium, write, print.

Phase 3 locks the frozen source dataclass and public signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. Pinned constants
2. Load combined, cleanup, load sample
3. Leftover medium sample
4. Local parquet, `put_new`, `RESULTS.md`, `main`
5. README and `.gitignore`

Phase 6 is complete when the live command exits 0 and the S3 object exists. Commit `RESULTS.md` and the changelog line after the live run.
