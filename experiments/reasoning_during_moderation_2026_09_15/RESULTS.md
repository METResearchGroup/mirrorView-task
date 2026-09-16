# Reasoning tokens on split versus unanimous moderation posts

Export `since_date=2026-09-09`, `csv_files=3081`, `split=2201`, `unanimous_keep=2260`, `unanimous_remove=214`.

## Experiment 1

| model_id | group | n_posts | n_valid | mean | median | p25 | p75 | max | truncated_rate | empty_thinking_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3.5-4B | split | 2201 | 2201 | 3081.0863 | 2975.0000 | 2253.0000 | 3826.0000 | 8004.0000 | 0.0000 | 0.0000 |
| Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 2260 | 3093.3699 | 2999.5000 | 2228.5000 | 3838.7500 | 7091.0000 | 0.0000 | 0.0000 |
| Qwen/Qwen3.5-4B | unanimous_remove | 214 | 214 | 2676.4673 | 2552.5000 | 1890.0000 | 3196.0000 | 5795.0000 | 0.0000 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2201 | 2200 | 622.3177 | 605.0000 | 494.0000 | 722.0000 | 1626.0000 | 0.0005 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 2260 | 669.0757 | 635.5000 | 526.0000 | 777.2500 | 2659.0000 | 0.0000 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 214 | 577.0654 | 554.0000 | 449.2500 | 663.5000 | 1374.0000 | 0.0000 | 0.0000 |

## Experiment 2

_No rows. GPU traces were not present in this environment._

## Experiment 3

Values are milliseconds.

| level | group | n | mean | median | p25 | p75 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trial | split | 9882 | 18208.9115 | 12628.3000 | 7478.8000 | 21907.2250 | 511827.0000 |
| trial | unanimous_keep | 9671 | 19830.3415 | 13782.5000 | 7934.0000 | 23577.6000 | 861190.3000 |
| trial | unanimous_remove | 913 | 16894.5399 | 9982.0000 | 6075.9000 | 16228.1000 | 2183057.0000 |
| post_mean | split | 2201 | 18210.6089 | 14918.6750 | 10804.4750 | 21707.8400 | 170052.0600 |
| post_mean | unanimous_keep | 2260 | 19842.5570 | 16133.5175 | 11536.5062 | 23370.0688 | 223575.7500 |
| post_mean | unanimous_remove | 214 | 17082.7457 | 11758.5825 | 8366.0062 | 17526.7725 | 583608.0000 |

## Experiment 4

| prompt_arm | model_id | group | n_valid | uncertainty_rate | revision_rate | tension_rate |
| --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | split | 2201 | 0.9932 | 0.9973 | 0.9973 |
| study | Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 0.9872 | 0.9987 | 0.9987 |
| study | Qwen/Qwen3.5-4B | unanimous_remove | 214 | 0.9860 | 0.9953 | 1.0000 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.9009 | 0.4982 | 0.9759 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.9345 | 0.5460 | 0.9717 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.7991 | 0.5327 | 0.9813 |

_No rows. GPU traces were not present in this environment._

Experiment 4 marker rates use experiment 1 traces. The paired experiment 1 versus experiment 2 comparison waits on experiment 2 traces. F1 and accuracy were not measured.
