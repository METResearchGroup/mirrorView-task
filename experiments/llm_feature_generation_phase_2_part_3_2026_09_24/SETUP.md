# Setup

## Data required

- Registry CSVs via `shared.data.dataloader.load_dataset` (S3-backed; uses lab AWS credentials when set):
  - `STUDY_PHASE_2_PART_2_AND_3_STIMULI` (20,000 posts, Part 2 + Part 3 union)
  - `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` (phase-1 moderation trials for both parts)
  - `STUDY_PHASE_2_PART_2_STIMULI` (Part 2 catalog for `in_part2_catalog`)
  - `STUDY_PHASE_2_PART_2_RESULTS_FULL` and `STUDY_PHASE_2_PART_3_RESULTS_FULL` (prolific_id membership for `collection` and filters)
- AWS credentials for S3 upload to `mirrorview-experimental-artifacts`.

## Participant filters

- `all` (default): all Part 2 and Part 3 labels in the union.
- `attention_pass`: drop Part 3 participants who failed the attention check; keep every Part 2 participant (Part 2 has no `attention_check_passed` column).
- `part3_only`: Part 3 labels only (Question 1 replication and sensitivity).

## Expected counts (participant_filter=all)

- 20,000 cohort rows; 20,000 with at least one phase-1 moderation label.
- Label histogram: zero with one or two labels; 20,000 with three or more.
- 10,000 posts overlap the Part 2 June catalog; 1,101 posts are new versus the prior Part 3-only stimuli.
- Three-group eligible (4+ raters): 10,761 posts (split 5,217; unanimous_keep 5,126; unanimous_remove 418).
- Modal keep rate: 75.70%.
- Stratified split with preservation: existing 18,899 posts keep their prior half; 1,101 new posts assigned 50/50 (seed 42).

## Split output

`split.py --seed 42 --write` reads committed `data/post_split/` CSVs, preserves prior discovery versus test assignments, stratifies only new union posts, writes updated CSVs and metadata, then sets the `split` column on the latest `participant_filter=all` cohort parquet under each text arm in place.
