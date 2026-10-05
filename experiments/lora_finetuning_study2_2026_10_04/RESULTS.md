# Study 2 LoRA keep/remove evaluation

## Unanimous adapter

Full-table vLLM inference on SageMaker **ml.g5.xlarge** (job `study2-vllm-eval-full-20261005-085719`). Adapter: **Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14** (unanimous-label training only). One forward pass over all 20,000 `STUDY_2_KEEP_REMOVE_LABELS` rows (prompts truncated to 4088 tokens from the left) produced metrics for the unanimous, split, and full-table slices below.

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS | 4051 | 0 | 0.9975 | 0.9686 | 1.0000 | 0.9840 |
| STUDY_2_KEEP_REMOVE_SPLIT_LABELS | 9941 | 0 | 0.7790 | 0.6483 | 0.3805 | 0.4795 |
| STUDY_2_KEEP_REMOVE_LABELS | 20000 | 0 | 0.8216 | 0.7360 | 0.4142 | 0.5301 |

Raw metrics: `results/unanimous/Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14/metrics.jsonl`.

## Split adapter

Full-table vLLM inference on SageMaker **ml.g5.xlarge** (job `study2-vllm-eval-full-20261005-122622`, billable **2004** s). Adapter: **Qwen3.5-4B_lora_split_2026_10_04-20:48:33** (split-label training).

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS | 4051 | 0 | 0.9657 | 0.7666 | 0.7890 | 0.7776 |
| STUDY_2_KEEP_REMOVE_SPLIT_LABELS | 9941 | 0 | 0.9439 | 0.8762 | 0.9203 | 0.8977 |
| STUDY_2_KEEP_REMOVE_LABELS | 20000 | 0 | 0.8980 | 0.8301 | 0.7296 | 0.7766 |

Raw metrics: `results/split/Qwen3.5-4B_lora_split_2026_10_04-20:48:33/metrics.jsonl`.

## All adapter

Full-table vLLM inference on SageMaker **ml.g5.xlarge** (job `study2-vllm-eval-full-20261005-130139`, billable **2004** s). Adapter: **Qwen3.5-4B_lora_all_2026_10_04-20:48:43** (all-label training).

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS | 4051 | 0 | 0.9938 | 0.9521 | 0.9675 | 0.9597 |
| STUDY_2_KEEP_REMOVE_SPLIT_LABELS | 9941 | 0 | 0.9506 | 0.8880 | 0.9331 | 0.9100 |
| STUDY_2_KEEP_REMOVE_LABELS | 20000 | 0 | 0.9634 | 0.9153 | 0.9360 | 0.9255 |

Raw metrics: `results/all/Qwen3.5-4B_lora_all_2026_10_04-20:48:43/metrics.jsonl`.
