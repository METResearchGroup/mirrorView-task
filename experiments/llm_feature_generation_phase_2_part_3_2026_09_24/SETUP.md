# Setup

## Data required

- Registry CSVs via `shared.data.dataloader.load_dataset`:
  - `STUDY_PHASE_2_PART_3_STIMULI` (18,899 posts)
  - `STUDY_PHASE_2_PART_3_RESULTS_FULL` (phase-1 moderation trials)
  - `STUDY_PHASE_2_PART_2_STIMULI` (Part 2 overlap for `in_part2_catalog`)
- AWS credentials for S3 upload to `mirrorview-experimental-artifacts`.

## Expected counts

- 18,899 cohort rows; 18,866 with at least one phase-1 moderation label.
- Label histogram: 1,145 with one label; 1,755 with two; 15,966 with three or more.
- 8,899 posts overlap the Part 2 June catalog.
- Stratified split: 9,449 discovery and 9,450 test post IDs (seed 42).

## Split output

`split.py --seed 42 --write` writes `data/post_split/` CSVs and metadata, then sets
the `split` column on the latest cohort parquet under each text arm in place.
