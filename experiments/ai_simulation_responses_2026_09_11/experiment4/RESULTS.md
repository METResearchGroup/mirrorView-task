# Experiment 4 results

## Cohort

998 unique prolific_ids from 1000 cohort user rows. Duplicate prolific_ids: 6a1094c7ef643bf92ae4828a, 6a1b6df9270d2d83bc80908f.

## User-level

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.6067 | 0.4069 | 0.6260 | 0.4377 |
| bedrock_micro_nova | 998 | 0.3818 | 0.3174 | 0.8251 | 0.4238 |
| bedrock_qwen | 998 | 0.6864 | 0.4810 | 0.4812 | 0.4294 |
| bedrock_claude | 997 | 0.7443 | 0.5507 | 0.3018 | 0.3511 |

scored_users openai=998 failed_users=0
scored_users bedrock_micro_nova=998 failed_users=0
scored_users bedrock_qwen=998 failed_users=0
scored_users bedrock_claude=997 failed_users=1

## Post-level

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 19960 | 0.3058 | 0.6067 | 0.4133 | 0.6825 | 0.5149 |
| bedrock_micro_nova | 19960 | 0.3058 | 0.3818 | 0.3220 | 0.9241 | 0.4776 |
| bedrock_qwen | 19960 | 0.3058 | 0.6864 | 0.4873 | 0.4912 | 0.4892 |
| bedrock_claude | 19940 | 0.3056 | 0.7443 | 0.6868 | 0.3001 | 0.4177 |

scored_pairs openai=19960 failed_users=0
scored_pairs bedrock_micro_nova=19960 failed_users=0
scored_pairs bedrock_qwen=19960 failed_users=0
scored_pairs bedrock_claude=19940 failed_users=1

## Party: party_group=democrat

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 598 | 0.6074 | 0.4206 | 0.6553 | 0.4579 |
| bedrock_micro_nova | 598 | 0.3922 | 0.3301 | 0.8495 | 0.4405 |
| bedrock_qwen | 598 | 0.6821 | 0.4932 | 0.4972 | 0.4414 |
| bedrock_claude | 597 | 0.7364 | 0.5592 | 0.3127 | 0.3620 |

scored_users openai=598 failed_users=0
scored_users bedrock_micro_nova=598 failed_users=0
scored_users bedrock_qwen=598 failed_users=0
scored_users bedrock_claude=597 failed_users=1

## Party: party_group=republican

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 400 | 0.6055 | 0.3866 | 0.5821 | 0.4074 |
| bedrock_micro_nova | 400 | 0.3663 | 0.2985 | 0.7886 | 0.3989 |
| bedrock_qwen | 400 | 0.6927 | 0.4628 | 0.4575 | 0.4115 |
| bedrock_claude | 400 | 0.7560 | 0.5380 | 0.2855 | 0.3349 |

scored_users openai=400 failed_users=0
scored_users bedrock_micro_nova=400 failed_users=0
scored_users bedrock_qwen=400 failed_users=0
scored_users bedrock_claude=400 failed_users=1

## Toxicity: sample_low_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 4792 | 0.1592 | 0.7225 | 0.2533 | 0.3814 | 0.3044 |
| bedrock_micro_nova | 4792 | 0.1592 | 0.2959 | 0.1687 | 0.8716 | 0.2827 |
| bedrock_qwen | 4792 | 0.1592 | 0.8057 | 0.2754 | 0.1350 | 0.1812 |
| bedrock_claude | 4788 | 0.1594 | 0.8406 | 0.5000 | 0.0328 | 0.0615 |

scored_pairs openai=4792 failed_users=0
scored_pairs bedrock_micro_nova=4792 failed_users=0
scored_pairs bedrock_qwen=4792 failed_users=0
scored_pairs bedrock_claude=4788 failed_users=1

## Toxicity: sample_middle_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.2775 | 0.5671 | 0.3483 | 0.6428 | 0.4518 |
| bedrock_micro_nova | 9980 | 0.2775 | 0.3507 | 0.2886 | 0.9151 | 0.4389 |
| bedrock_qwen | 9980 | 0.2775 | 0.6701 | 0.4037 | 0.3958 | 0.3997 |
| bedrock_claude | 9970 | 0.2771 | 0.7426 | 0.6105 | 0.1969 | 0.2978 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9970 failed_users=1

## Toxicity: sample_high_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 5188 | 0.4958 | 0.5758 | 0.5486 | 0.8145 | 0.6556 |
| bedrock_micro_nova | 5188 | 0.4958 | 0.5210 | 0.5091 | 0.9495 | 0.6628 |
| bedrock_qwen | 5188 | 0.4958 | 0.6074 | 0.5873 | 0.6995 | 0.6385 |
| bedrock_claude | 5182 | 0.4956 | 0.6584 | 0.7317 | 0.4907 | 0.5874 |

scored_pairs openai=5188 failed_users=0
scored_pairs bedrock_micro_nova=5188 failed_users=0
scored_pairs bedrock_qwen=5188 failed_users=0
scored_pairs bedrock_claude=5182 failed_users=1

## Stance: left

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3086 | 0.6121 | 0.4227 | 0.7026 | 0.5279 |
| bedrock_micro_nova | 9980 | 0.3086 | 0.3883 | 0.3278 | 0.9347 | 0.4854 |
| bedrock_qwen | 9980 | 0.3086 | 0.6927 | 0.5020 | 0.5308 | 0.5160 |
| bedrock_claude | 9970 | 0.3083 | 0.7548 | 0.7248 | 0.3299 | 0.4534 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9970 failed_users=1

## Stance: right

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3030 | 0.6012 | 0.4036 | 0.6620 | 0.5015 |
| bedrock_micro_nova | 9980 | 0.3030 | 0.3754 | 0.3162 | 0.9134 | 0.4698 |
| bedrock_qwen | 9980 | 0.3030 | 0.6801 | 0.4708 | 0.4507 | 0.4606 |
| bedrock_claude | 9970 | 0.3029 | 0.7338 | 0.6448 | 0.2699 | 0.3805 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9970 failed_users=1
