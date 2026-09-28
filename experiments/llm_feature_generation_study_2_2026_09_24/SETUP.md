# Setup

## Data required

- Registry CSVs via `shared.data.dataloader.load_dataset` (S3-backed; uses lab AWS credentials when set):
  - `STUDY_2_STIMULI` (20,000 posts, Study 2 union)
  - `STUDY_2_RESULTS_FULL` (phase-1 moderation trials)
  - June collection stimuli and session export, for `in_june_catalog` and `collection`
  - September collection stimuli, for `participant_filter=september_only`
- AWS credentials for S3 upload to `mirrorview-experimental-artifacts`.

## Participant filters

- `all` (default): all Study 2 labels in the union.
- `attention_pass`: drop September participants who failed the attention check; keep every June participant (June collection has no `attention_check_passed` column).
- `september_only`: September labels only (Question 1 replication and sensitivity).

## Expected counts (participant_filter=all)

- 20,000 cohort rows; 20,000 with at least one phase-1 moderation label.
- Label histogram: zero with one or two labels; 20,000 with three or more.
- 10,000 posts are in the June catalog; 1,101 posts are new versus the prior September-only stimuli.
- Three-group eligible (4+ raters): 10,761 posts (split 5,217; unanimous_keep 5,126; unanimous_remove 418).
- Modal keep rate: 75.70%.
- Stratified split with preservation: existing 18,899 posts keep their prior half; 1,101 new posts assigned 50/50 (seed 42).

## Split output

`split.py --seed 42 --write` reads `data/post_split/` from S3 (`s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_study_2_2026_09_24/data/post_split/`), preserves prior discovery versus test assignments, stratifies only new union posts, writes updated CSVs and metadata, then sets the `split` column on the latest `participant_filter=all` cohort parquet under each text arm in place.
