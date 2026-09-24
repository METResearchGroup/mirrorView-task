# Setup

Required data (load with `shared.data.dataloader.load_dataset` from `s3://mirrorview-experimental-artifacts/`):

| Registry name | Role | Counts |
| --- | --- | --- |
| `STUDY_PHASE_2_PART_2_AND_3_STIMULI` | Stimulus catalog (`post_primary_key`, `original_text`, `mirrored_text`, facets) | 20,000 unique posts: Part 2 catalog 10,000, Part 3 catalog 18,899, overlap 8,899 identical texts/facets. On overlap, the union keeps the Part 2 row. |
| `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` | Linked-fate session export | 168,871 rows, 5,051 Prolific accounts (1,176 Part 2 only, 3,875 Part 3 only, no account overlap). Includes 108,213 scored `linked_fate` ratings. |
| `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` | Modal keep/remove per post (outcomes only; not used to fit topics) | 20,000 posts, 103,060 ratings, 15,140 keep / 4,860 remove. Every post has at least 3 raters. |

Keep/remove labels are built from the combined results table with `shared/data/transformed/study_phase_2_part_2_and_3/transform.py` (materializes `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels.csv`).

S3 keys for the raw CSVs follow the repo layout under `shared/data/raw/study_phase_2_part_2_and_3/`. See `shared/data/raw/study_phase_2_part_2_and_3/README.md`.
