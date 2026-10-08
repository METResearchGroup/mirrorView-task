# Study 2 LoRA keep/remove evaluation

Each adapter was scored once with vLLM on SageMaker `ml.g5.xlarge`. The gold label on every row is the modal decision: keep when keep votes strictly outnumber remove votes, and remove otherwise. With five labelers there is no tie, so that modal label is the majority.

Unanimous rows are the five-labeler posts with 0 or 5 remove votes. Split rows are the five-labeler posts with 1, 2, 3, or 4 remove votes. The all-labels row in each table is those two sets together (13,992 posts). Posts with any other labeler count are left out. The positive class is remove. No generation was invalid.

The unanimous and split rows match `metrics.jsonl`. The all-labels row was recomputed from the same `preds.jsonl` by keeping only rows in one of those two sets. The `metrics.jsonl` line for `STUDY_2_KEEP_REMOVE_LABELS` is the broader 20,000-row table and is not the number reported here.

## Unanimous adapter

Job `study2-vllm-eval-full-20261005-085719`. Adapter `Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14`.

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unanimous | 4051 | 0 | 0.9975 | 0.9686 | 1.0000 | 0.9840 |
| Split | 9941 | 0 | 0.7790 | 0.6483 | 0.3805 | 0.4795 |
| All labels | 13992 | 0 | 0.8423 | 0.7025 | 0.4447 | 0.5447 |

## Split adapter

Job `study2-vllm-eval-full-20261005-122622` (2,004 s). Adapter `Qwen3.5-4B_lora_split_2026_10_04-20:48:33`.

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unanimous | 4051 | 0 | 0.9657 | 0.7666 | 0.7890 | 0.7776 |
| Split | 9941 | 0 | 0.9439 | 0.8762 | 0.9203 | 0.8977 |
| All labels | 13992 | 0 | 0.9502 | 0.8650 | 0.9067 | 0.8853 |

## All-label adapter

Job `study2-vllm-eval-full-20261005-130139` (2,004 s). Adapter `Qwen3.5-4B_lora_all_2026_10_04-20:48:43`.

| dataset | n | n_invalid | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unanimous | 4051 | 0 | 0.9938 | 0.9521 | 0.9675 | 0.9597 |
| Split | 9941 | 0 | 0.9506 | 0.8880 | 0.9331 | 0.9100 |
| All labels | 13992 | 0 | 0.9631 | 0.8945 | 0.9367 | 0.9151 |
