# Prompt engineering keep/remove classifier results

- Model: `qwen/qwen3.6-plus`
- Subset: `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (n=1000, seed=42, balanced 500 keep / 500 remove)
- Response schema: `shared.schemas.IsRemoveResult`
- Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
- Control run dir: `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/2026_08_06-00:23:40.261093`
- Tuned run dir: `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/tuned/outputs/2026_08_06-00:30:36.500724`

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| control | 0.6600 | 0.6932 | 0.5740 | 0.6280 |
| prompt-tuned | 0.6490 | 0.6114 | 0.8180 | 0.6997 |
