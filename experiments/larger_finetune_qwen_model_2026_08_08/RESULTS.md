# Qwen3-4B LoRA fine-tune keep/remove results

- Model: `Qwen/Qwen3-4B-Instruct-2507`
- Data: modal keep/remove labels, balanced 1:1 (all removes + equal keeps); seed=1; 80/20
- Positive class: remove
- Exploratory teachability run (no numeric success bar)

## Train

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6027 | 0.5641 | 0.9031 | 0.6945 |
| fine-tuned | 0.7293 | 0.7382 | 0.7107 | 0.7242 |

## Test

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6385 | 0.5871 | 0.9343 | 0.7210 |
| fine-tuned | 0.7016 | 0.7090 | 0.6838 | 0.6962 |
