# Setup

The comparison uses two existing tables.

- Human labels come from `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` in `s3://mirrorview-experimental-artifacts/shared/data/raw/study_phase_2_part_2_and_3/results/full.csv`. Load that name with `shared.data.dataloader.load_dataset`.
- Jev probabilities come from `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline_union/A1_pair_study_prompt/labels.parquet`. The file has 19,219 rows. The probability column is `p_remove`, and it has no missing values. The join key is `post_id`.

Keep moderation trials whose decision is `keep` or `remove`. The export has no `skip` decision on those trials. Keep one row per `prolific_id` and `post_id`, then keep posts with exactly five labelers. The comparison is the inner join of that set with the Jev file.
