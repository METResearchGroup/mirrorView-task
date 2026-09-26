# Setup

You need two existing tables for the comparison.

- Human labels are `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` in `s3://mirrorview-experimental-artifacts/shared/data/raw/study_phase_2_part_2_and_3/results/full.csv`. Load `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` with `shared.data.dataloader.load_dataset`.
- Jev probabilities are in `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline_union/A1_pair_study_prompt/labels.parquet`. The file has 19,219 rows. The probability column is `p_remove`, and it has no missing values. The join key is `post_id`.

From the human labels, keep moderation trials whose decision is `keep` or `remove`. The export has no `skip` decision on those trials. Keep one row per `prolific_id` and `post_id`, so each person has one vote per post. Next, keep posts with exactly five labelers. The comparison is the inner join of the filtered posts with the Jev file.
