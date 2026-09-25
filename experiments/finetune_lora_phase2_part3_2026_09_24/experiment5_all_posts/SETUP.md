# Experiment 5 setup (data)

## Gold table

- `data/all_posts.csv`: 20,000 posts built from the combined Part 2 and Part 3 study table via the shared dataloader (`shared/data/transformed/study_phase_2_part_2_and_3`), with the same trial filter and modal aggregation as the union label file. Columns include `message_id`, modal `decision` / `keep_remove_label`, `n_raters`, `n_remove`, train vs test `split`, and `in_unanimous` from `experiments/finetune_lora_phase2_part3_2026_09_24/data/split_manifest.csv`.

## Model inputs

- Merged weights (or equivalent inference artifacts) for the Part 3 unanimous adapter (`experiment1_unanimous`) and modal adapter (`experiment2_modal`), produced in this experiment’s merge step.
- Prediction CSVs (one row per post, same columns as held-out inference runs):
  - `preds/unanimous_model/all_posts.csv`
  - `preds/modal_model/all_posts.csv`

Scoring compares predictions to the modal label on `all_posts.csv` (including train posts for the all_posts and train slices).
