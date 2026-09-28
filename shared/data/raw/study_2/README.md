# Study 2

The full linked-fate dataset. These tables are the Part 2 collection followed by the Part 3 collection. The CSVs are in `s3://mirrorview-experimental-artifacts/` at the repo-relative keys below.

- `shared/data/raw/study_2/results/full.csv`: 168,871 session rows and 5,051 Prolific accounts. Part 3-only columns are empty on Part 2 rows.
- `shared/data/raw/study_2/stimuli/flips.csv`: 20,000 unique posts. Overlapping `post_primary_key` values keep the Part 2 row.

Load either table with `shared.data.dataloader.load_dataset`. The names are `STUDY_2_RESULTS_FULL` and `STUDY_2_STIMULI`.
