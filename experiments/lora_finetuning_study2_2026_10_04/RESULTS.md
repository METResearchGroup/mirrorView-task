# Study 2 LoRA keep/remove evaluation (unanimous adapter)

Full-table vLLM inference on SageMaker **ml.g5.xlarge** (job `study2-vllm-eval-full-20261005-085719`). Adapter: **Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14** (unanimous-label training only). One forward pass over all 20,000 `STUDY_2_KEEP_REMOVE_LABELS` rows (prompts truncated to 4088 tokens from the left) produced metrics for the unanimous, split, and full-table slices below. The **all-label** training adapter was not scored.

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS | 4051 | 0 | 0.9975 | 0.9686 | 1.0000 | 0.9840 |
| STUDY_2_KEEP_REMOVE_SPLIT_LABELS | 9941 | 0 | 0.7790 | 0.6483 | 0.3805 | 0.4795 |
| STUDY_2_KEEP_REMOVE_LABELS | 20000 | 0 | 0.8216 | 0.7360 | 0.4142 | 0.5301 |

Raw metrics: `results/unanimous/Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14/metrics.jsonl`.
