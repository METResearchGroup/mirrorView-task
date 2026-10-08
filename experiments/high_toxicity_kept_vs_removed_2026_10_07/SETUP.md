# Setup

This experiment reads stored files. It does not refit topics or relabel features.

| Input | Location |
| --- | --- |
| Keep/remove labels | `STUDY_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset` |
| Topic assignments | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/topics/original/20260924T135151Z/assignments.parquet` |
| Topic names | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/labels/original/20260924T135628Z/topic_labels.parquet` |
| Topic-by-toxicity keep rates | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/analyses/outcomes/20260924T140052Z/outcomes_by_topic_facet.csv` |
| Feature labels | `s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/step6_label_posts_with_features/post_feature_labels.parquet` |

Feature names come from `LABEL_TO_DETAIL` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`. A feature is present when that file already stores 1, which is the 0.7 cutoff in `FEATURE_PRESENT_THRESHOLD`.

The population is posts with `sample_toxicity_type` equal to `sample_high_toxicity`, at least 3 raters, and a row in the original-post topic assignments. That is 4,983 posts. Keep versus remove is the stored `decision` column. A tie is remove.

Run from the repo root. The script reads `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` from the environment or from `.env`.

```bash
PYTHONPATH=. uv run python experiments/high_toxicity_kept_vs_removed_2026_10_07/src/analyze.py
```

Tables and figures are written under `outputs/` and uploaded to `s3://mirrorview-experimental-artifacts/experiments/high_toxicity_kept_vs_removed_2026_10_07/`.
