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

Split posts do not have a higher mean thinking-token count than unanimous keep posts on these traces.

Qwen/Qwen3.5-4B split is not higher than keep (split=3081.1, keep=3093.4, remove=2676.5). The longest group is unanimous_keep, and the shortest is unanimous_remove. n_valid is 2201 split, 2260 keep, and 214 remove.

deepseek-ai/DeepSeek-R1-Distill-Qwen-7B split is not higher than keep (split=622.3, keep=669.1, remove=577.1). The longest group is unanimous_keep, and the shortest is unanimous_remove. n_valid is 2200 split, 2260 keep, and 214 remove.

## Experiment 2

| model_id | group | n_posts | n_valid | mean | median | p25 | p75 | max | truncated_rate | empty_thinking_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3.5-4B | split | 2201 | 2201 | 3251.1931 | 3089.0000 | 2396.0000 | 3941.0000 | 7773.0000 | 0.0000 | 0.0000 |
| Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 2257 | 3914.9637 | 3821.0000 | 3073.0000 | 4668.0000 | 8030.0000 | 0.0013 | 0.0000 |
| Qwen/Qwen3.5-4B | unanimous_remove | 214 | 213 | 2662.1033 | 2565.0000 | 1990.0000 | 3116.0000 | 5821.0000 | 0.0047 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2201 | 2200 | 678.1164 | 645.0000 | 516.0000 | 820.0000 | 1704.0000 | 0.0005 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 2260 | 687.8491 | 662.0000 | 531.5000 | 821.0000 | 1711.0000 | 0.0000 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 214 | 612.0654 | 577.5000 | 464.0000 | 724.5000 | 1385.0000 | 0.0000 | 0.0000 |

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

Broad family rates:

Broad rates count any confirmed phrase or token. Qwen values near 1.0 are a length and lexicon ceiling, because `wait`, `however`, and `both posts` fire on almost every long span. Do not treat those rates as a group contrast.

| prompt_arm | model_id | group | n_valid | uncertainty_rate | revision_rate | tension_rate |
| --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | split | 2201 | 0.9932 | 0.9973 | 0.9973 |
| study | Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 0.9872 | 0.9987 | 0.9987 |
| study | Qwen/Qwen3.5-4B | unanimous_remove | 214 | 0.9860 | 0.9953 | 1.0000 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.9009 | 0.4982 | 0.9759 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.9345 | 0.5460 | 0.9717 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.7991 | 0.5327 | 0.9813 |
| study_plus_criteria | Qwen/Qwen3.5-4B | split | 2201 | 0.9691 | 0.9964 | 0.9964 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_keep | 2257 | 0.9907 | 0.9965 | 0.9965 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_remove | 213 | 0.9484 | 0.9859 | 1.0000 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.6486 | 0.5095 | 0.9491 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.6881 | 0.4814 | 0.9588 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.5093 | 0.5701 | 0.9346 |

Strict family rates:

Strict rates drop generic chain-of-thought tokens (`however`, `maybe`, `wait`, `actually`, `instead`, `perhaps`, `probably`, `possibly`), the discourse phrase `on the other hand`, and prompt-echo items (`both posts`, `opposite`). Density is the number of distinct strict items per 1,000 thinking tokens.

| prompt_arm | model_id | group | n_valid | uncertainty_rate | revision_rate | tension_rate | uncertainty_density | revision_density | tension_density |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | split | 2201 | 0.5293 | 0.3053 | 0.5175 | 0.1980 | 0.1034 | 0.2269 |
| study | Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 0.4650 | 0.2735 | 0.5142 | 0.1752 | 0.0917 | 0.2304 |
| study | Qwen/Qwen3.5-4B | unanimous_remove | 214 | 0.4813 | 0.2243 | 0.5374 | 0.1938 | 0.0873 | 0.2427 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.1077 | 0.0018 | 0.1455 | 0.1863 | 0.0029 | 0.2483 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.1239 | 0.0031 | 0.1668 | 0.1991 | 0.0053 | 0.2659 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.0654 | 0.0093 | 0.1262 | 0.1215 | 0.0162 | 0.2267 |
| study_plus_criteria | Qwen/Qwen3.5-4B | split | 2201 | 0.4357 | 0.0741 | 0.3008 | 0.1483 | 0.0231 | 0.1139 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_keep | 2257 | 0.6221 | 0.1586 | 0.3775 | 0.1790 | 0.0412 | 0.1222 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_remove | 213 | 0.2958 | 0.0235 | 0.2300 | 0.1129 | 0.0088 | 0.0988 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.0891 | 0.0005 | 0.0332 | 0.1461 | 0.0007 | 0.0523 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.0934 | 0.0018 | 0.0381 | 0.1396 | 0.0026 | 0.0560 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.0421 | 0.0000 | 0.0093 | 0.0687 | 0.0000 | 0.0153 |

Phrase-only family rates:

Phrase-only rates ignore bag-of-words tokens. Tension phrase rates stay high when `both posts` is common, because that phrase is in the prompt.

| prompt_arm | model_id | group | n_valid | uncertainty_rate | revision_rate | tension_rate |
| --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | split | 2201 | 0.0695 | 0.0068 | 0.9846 |
| study | Qwen/Qwen3.5-4B | unanimous_keep | 2260 | 0.0942 | 0.0058 | 0.9832 |
| study | Qwen/Qwen3.5-4B | unanimous_remove | 214 | 0.0187 | 0.0000 | 0.9860 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.5986 | 0.0000 | 0.9318 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.5942 | 0.0004 | 0.9504 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.4673 | 0.0000 | 0.9393 |
| study_plus_criteria | Qwen/Qwen3.5-4B | split | 2201 | 0.0182 | 0.0005 | 0.9859 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_keep | 2257 | 0.0239 | 0.0009 | 0.9854 |
| study_plus_criteria | Qwen/Qwen3.5-4B | unanimous_remove | 213 | 0.0235 | 0.0000 | 0.9859 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2200 | 0.2100 | 0.0000 | 0.9045 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 0.2332 | 0.0000 | 0.9217 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 0.1589 | 0.0000 | 0.8879 |

Strict group contrasts:

Split minus keep and split minus remove on the strict rates and densities. Rate is the share of valid traces. Density is distinct strict item hits per 1,000 thinking tokens.

| prompt_arm | model_id | family | metric | split | keep | remove | split_minus_keep | split_minus_remove |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | uncertainty | rate | 0.5293 | 0.4650 | 0.4813 | 0.0643 | 0.0480 |
| study | Qwen/Qwen3.5-4B | uncertainty | density | 0.1980 | 0.1752 | 0.1938 | 0.0228 | 0.0042 |
| study | Qwen/Qwen3.5-4B | revision | rate | 0.3053 | 0.2735 | 0.2243 | 0.0319 | 0.0810 |
| study | Qwen/Qwen3.5-4B | revision | density | 0.1034 | 0.0917 | 0.0873 | 0.0117 | 0.0161 |
| study | Qwen/Qwen3.5-4B | tension | rate | 0.5175 | 0.5142 | 0.5374 | 0.0033 | -0.0199 |
| study | Qwen/Qwen3.5-4B | tension | density | 0.2269 | 0.2304 | 0.2427 | -0.0035 | -0.0157 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | rate | 0.1077 | 0.1239 | 0.0654 | -0.0162 | 0.0423 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | density | 0.1863 | 0.1991 | 0.1215 | -0.0128 | 0.0648 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | rate | 0.0018 | 0.0031 | 0.0093 | -0.0013 | -0.0075 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | density | 0.0029 | 0.0053 | 0.0162 | -0.0024 | -0.0133 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | rate | 0.1455 | 0.1668 | 0.1262 | -0.0214 | 0.0193 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | density | 0.2483 | 0.2659 | 0.2267 | -0.0175 | 0.0216 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | rate | 0.4357 | 0.6221 | 0.2958 | -0.1864 | 0.1399 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | density | 0.1483 | 0.1790 | 0.1129 | -0.0308 | 0.0354 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | rate | 0.0741 | 0.1586 | 0.0235 | -0.0846 | 0.0506 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | density | 0.0231 | 0.0412 | 0.0088 | -0.0181 | 0.0142 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | rate | 0.3008 | 0.3775 | 0.2300 | -0.0767 | 0.0707 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | density | 0.1139 | 0.1222 | 0.0988 | -0.0083 | 0.0151 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | rate | 0.0891 | 0.0934 | 0.0421 | -0.0043 | 0.0470 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | density | 0.1461 | 0.1396 | 0.0687 | 0.0065 | 0.0774 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | rate | 0.0005 | 0.0018 | 0.0000 | -0.0013 | 0.0005 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | density | 0.0007 | 0.0026 | 0.0000 | -0.0019 | 0.0007 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | rate | 0.0332 | 0.0381 | 0.0093 | -0.0049 | 0.0238 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | density | 0.0523 | 0.0560 | 0.0153 | -0.0037 | 0.0370 |

Item group contrasts:

Items whose split rate differs from the keep rate by at least 0.03. Positive split minus keep means the item is more common on split posts.

| prompt_arm | model_id | family | kind | item | split | keep | remove | split_minus_keep |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | uncertainty | token | borderline | 0.4598 | 0.3748 | 0.4486 | 0.0850 |
| study | Qwen/Qwen3.5-4B | tension | token | conflict | 0.3585 | 0.3058 | 0.4159 | 0.0527 |
| study | Qwen/Qwen3.5-4B | revision | token | reconsider | 0.3008 | 0.2633 | 0.2243 | 0.0375 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | perhaps | 0.1572 | 0.1905 | 0.1315 | -0.0333 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | however | 0.9437 | 0.9783 | 0.8826 | -0.0346 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | ambiguous | 0.0577 | 0.0944 | 0.0282 | -0.0367 |
| study | Qwen/Qwen3.5-4B | tension | token | opposite | 0.8937 | 0.9327 | 0.8224 | -0.0391 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | probably | 0.2894 | 0.3456 | 0.2535 | -0.0562 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | token | conflict | 0.2172 | 0.2796 | 0.1455 | -0.0624 |
| study | Qwen/Qwen3.5-4B | tension | token | conflicting | 0.0745 | 0.1381 | 0.0187 | -0.0635 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | token | opposite | 0.7697 | 0.8343 | 0.7042 | -0.0646 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | actually | 0.8292 | 0.9039 | 0.7465 | -0.0747 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | reconsider | 0.0695 | 0.1506 | 0.0235 | -0.0811 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | maybe | 0.5679 | 0.6850 | 0.4648 | -0.1171 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | borderline | 0.4121 | 0.5897 | 0.2582 | -0.1776 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | instead | 0.3682 | 0.3071 | 0.4907 | 0.0611 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | instead | 0.3682 | 0.3367 | 0.4299 | 0.0315 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | wait | 0.1455 | 0.1788 | 0.0701 | -0.0333 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | maybe | 0.3682 | 0.4058 | 0.2617 | -0.0376 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | however | 0.4900 | 0.5358 | 0.3224 | -0.0458 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | perhaps | 0.1777 | 0.2381 | 0.1449 | -0.0603 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | wait | 0.1323 | 0.2159 | 0.1121 | -0.0837 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | however | 0.6823 | 0.8044 | 0.5888 | -0.1222 |

High-frequency marker items:

Item rates are the share of valid traces containing that phrase or token. Rows below are model-level (groups pooled) for items at or above 0.05.

| prompt_arm | model_id | family | kind | item | n_valid | rate |
| --- | --- | --- | --- | --- | --- | --- |
| study | Qwen/Qwen3.5-4B | revision | token | wait | 4675 | 0.9968 |
| study | Qwen/Qwen3.5-4B | tension | phrase | both posts | 4675 | 0.9833 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | however | 4675 | 0.9831 |
| study | Qwen/Qwen3.5-4B | tension | token | opposite | 4675 | 0.9093 |
| study | Qwen/Qwen3.5-4B | revision | token | actually | 4675 | 0.8990 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | maybe | 4675 | 0.5870 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | borderline | 4675 | 0.4182 |
| study | Qwen/Qwen3.5-4B | tension | token | conflict | 4675 | 0.3356 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | probably | 4675 | 0.2982 |
| study | Qwen/Qwen3.5-4B | revision | token | reconsider | 4675 | 0.2791 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | perhaps | 4675 | 0.2785 |
| study | Qwen/Qwen3.5-4B | revision | token | instead | 4675 | 0.1829 |
| study | Qwen/Qwen3.5-4B | tension | token | tension | 4675 | 0.1132 |
| study | Qwen/Qwen3.5-4B | tension | token | conflicting | 4675 | 0.1027 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | ambiguous | 4675 | 0.0948 |
| study | Qwen/Qwen3.5-4B | tension | token | inconsistent | 4675 | 0.0657 |
| study | Qwen/Qwen3.5-4B | uncertainty | token | possibly | 4675 | 0.0616 |
| study | Qwen/Qwen3.5-4B | uncertainty | phrase | hard to say | 4675 | 0.0528 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | phrase | both posts | 4674 | 0.9409 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | however | 4674 | 0.7371 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | token | opposite | 4674 | 0.6444 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | phrase | on the other hand | 4674 | 0.5518 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | maybe | 4674 | 0.3815 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | instead | 4674 | 0.3558 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | perhaps | 4674 | 0.2054 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | wait | 4674 | 0.1718 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | probably | 4674 | 0.1361 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | token | conflict | 4674 | 0.1209 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | actually | 4674 | 0.1057 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | possibly | 4674 | 0.0774 |
| study | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | phrase | not sure | 4674 | 0.0700 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | wait | 4671 | 0.9955 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | phrase | both posts | 4671 | 0.9852 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | however | 4671 | 0.9576 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | actually | 4671 | 0.8615 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | token | opposite | 4671 | 0.7979 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | maybe | 4671 | 0.6198 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | borderline | 4671 | 0.4909 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | probably | 4671 | 0.3149 |
| study_plus_criteria | Qwen/Qwen3.5-4B | tension | token | conflict | 4671 | 0.2441 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | instead | 4671 | 0.2235 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | perhaps | 4671 | 0.1721 |
| study_plus_criteria | Qwen/Qwen3.5-4B | revision | token | reconsider | 4671 | 0.1066 |
| study_plus_criteria | Qwen/Qwen3.5-4B | uncertainty | token | ambiguous | 4671 | 0.0741 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | phrase | both posts | 4674 | 0.9116 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | however | 4674 | 0.5045 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | tension | token | opposite | 4674 | 0.4181 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | instead | 4674 | 0.3442 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | maybe | 4674 | 0.2619 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | phrase | on the other hand | 4674 | 0.1761 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | wait | 4674 | 0.1581 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | perhaps | 4674 | 0.1014 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | revision | token | actually | 4674 | 0.0794 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | probably | 4674 | 0.0620 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | token | possibly | 4674 | 0.0586 |
| study_plus_criteria | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | uncertainty | phrase | not sure | 4674 | 0.0541 |

Paired experiment 1 versus experiment 2:

| model_id | group | n_paired | mean_thinking_token_diff | mean_uncertainty_diff | mean_revision_diff | mean_tension_diff |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3.5-4B | split | 2201 | 170.1068 | -0.0241 | -0.0009 | -0.0009 |
| Qwen/Qwen3.5-4B | unanimous_keep | 2257 | 821.4479 | 0.0035 | -0.0022 | -0.0022 |
| Qwen/Qwen3.5-4B | unanimous_remove | 213 | -10.9202 | -0.0376 | -0.0094 | 0.0000 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | split | 2199 | 55.8236 | -0.2519 | 0.0118 | -0.0268 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_keep | 2260 | 18.7735 | -0.2465 | -0.0646 | -0.0128 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | unanimous_remove | 214 | 35.0000 | -0.2897 | 0.0374 | -0.0467 |

Broad family rates sit near 1.0 on Qwen, so they do not distinguish groups. Those rates fire because `wait`, `however`, and `both posts` appear in almost every long thinking span. The statements below use the strict rates, which drop those generic tokens, `on the other hand`, and the prompt-echo items.

study Qwen/Qwen3.5-4B: strict uncertainty rates are 0.529 on split, 0.465 on keep, and 0.481 on remove. Split minus keep is +0.064 (SE 0.015), which is larger than sampling noise. Strict revision rates are 0.305, 0.273, and 0.224. Strict tension rates are 0.517, 0.514, and 0.537. Uncertainty density is 0.198, 0.175, and 0.194 distinct strict items per 1,000 thinking tokens.

study deepseek-ai/DeepSeek-R1-Distill-Qwen-7B: strict uncertainty rates are 0.108 on split, 0.124 on keep, and 0.065 on remove. Split minus keep is -0.016 (SE 0.010), which is inside sampling noise. Strict revision rates are 0.002, 0.003, and 0.009. Strict tension rates are 0.145, 0.167, and 0.126. Uncertainty density is 0.186, 0.199, and 0.121 distinct strict items per 1,000 thinking tokens.

study_plus_criteria Qwen/Qwen3.5-4B: strict uncertainty rates are 0.436 on split, 0.622 on keep, and 0.296 on remove. Split minus keep is -0.186 (SE 0.015), which is larger than sampling noise. Strict revision rates are 0.074, 0.159, and 0.023. Strict tension rates are 0.301, 0.377, and 0.230. Uncertainty density is 0.148, 0.179, and 0.113 distinct strict items per 1,000 thinking tokens.

study_plus_criteria deepseek-ai/DeepSeek-R1-Distill-Qwen-7B: strict uncertainty rates are 0.089 on split, 0.093 on keep, and 0.042 on remove. Split minus keep is -0.004 (SE 0.009), which is inside sampling noise. Strict revision rates are 0.000, 0.002, and 0.000. Strict tension rates are 0.033, 0.038, and 0.009. Uncertainty density is 0.146, 0.140, and 0.069 distinct strict items per 1,000 thinking tokens.

If uncertainty density is close across groups, a higher rate means a larger share of traces contain at least one strict item, not more uncertainty language per token.

Phrase-only uncertainty ignores bag-of-words tokens, so it is the narrower reading of explicit hedging language. The phrase list still includes `on the other hand` and `both posts`, so DeepSeek phrase-only uncertainty and both models' phrase-only tension can stay high even when strict rates do not.

study Qwen/Qwen3.5-4B: phrase-only uncertainty is 0.070 on split, 0.094 on keep, and 0.019 on remove, so keep is higher than split. Phrase-only tension is 0.985, 0.983, and 0.986, and that family is still mostly `both posts`.

study deepseek-ai/DeepSeek-R1-Distill-Qwen-7B: phrase-only uncertainty is 0.599 on split, 0.594 on keep, and 0.467 on remove, so split and keep are within sampling noise. Phrase-only tension is 0.932, 0.950, and 0.939, and that family is still mostly `both posts`.

study_plus_criteria Qwen/Qwen3.5-4B: phrase-only uncertainty is 0.018 on split, 0.024 on keep, and 0.023 on remove, so split and keep are within sampling noise. Phrase-only tension is 0.986, 0.985, and 0.986, and that family is still mostly `both posts`.

study_plus_criteria deepseek-ai/DeepSeek-R1-Distill-Qwen-7B: phrase-only uncertainty is 0.210 on split, 0.233 on keep, and 0.159 on remove, so split and keep are within sampling noise. Phrase-only tension is 0.905, 0.922, and 0.888, and that family is still mostly `both posts`.

Qwen/Qwen3.5-4B split: experiment 2 thinking-token mean is not lower than experiment 1 (diff=170.107). Qwen/Qwen3.5-4B unanimous_keep: experiment 2 thinking-token mean is not lower than experiment 1 (diff=821.448). Qwen/Qwen3.5-4B unanimous_remove: experiment 2 thinking-token mean is lower than experiment 1 (diff=-10.920). deepseek-ai/DeepSeek-R1-Distill-Qwen-7B split: experiment 2 thinking-token mean is not lower than experiment 1 (diff=55.824). deepseek-ai/DeepSeek-R1-Distill-Qwen-7B unanimous_keep: experiment 2 thinking-token mean is not lower than experiment 1 (diff=18.773). deepseek-ai/DeepSeek-R1-Distill-Qwen-7B unanimous_remove: experiment 2 thinking-token mean is not lower than experiment 1 (diff=35.000). F1 and accuracy were not measured.
