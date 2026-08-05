# Prompt engineering keep/remove classifier results

- Model: `gpt-5.4-nano`
- Subset: `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (n=500, seed=42)
- Response schema: `shared.schemas.IsRemoveResult`
- Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
- Control run dir: `experiments/llm_prompt_engineering_2026_08_05/outputs/control/outputs/2026_08_05-15:13:22.069430`
- Tuned run dir: `experiments/llm_prompt_engineering_2026_08_05/outputs/tuned/outputs/2026_08_05-15:18:16.437537`

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| control | 0.6940 | 0.5425 | 0.6725 | 0.6005 |
| prompt-tuned | 0.5560 | 0.4278 | 0.8830 | 0.5763 |
