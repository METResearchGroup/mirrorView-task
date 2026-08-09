# Qwen3-4B LoRA fine-tune keep/remove results

- Model: `Qwen/Qwen3-4B-Instruct-2507`
- Data: unanimous min-3 balanced n=308; seed=1; 80/20
- Positive class: remove
- Exploratory teachability run (no numeric success bar)

## Train

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6870 | 0.6173 | 0.9837 | 0.7586 |
| fine-tuned | 0.9715 | 0.9833 | 0.9593 | 0.9712 |

## Test

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| baseline | 0.6613 | 0.6000 | 0.9677 | 0.7407 |
| fine-tuned | 0.9677 | 0.9394 | 1.0000 | 0.9688 |
