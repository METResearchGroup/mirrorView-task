# Experiment 1 results

## Cohort

998 unique prolific_ids from 1000 cohort user rows. Duplicate prolific_ids: 6a1094c7ef643bf92ae4828a, 6a1b6df9270d2d83bc80908f.

## User-level

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.5533 | 0.3562 | 0.5915 | 0.3853 |
| bedrock_micro_nova | 996 | 0.3567 | 0.3135 | 0.8319 | 0.4209 |
| bedrock_qwen | 998 | 0.6582 | 0.4572 | 0.4724 | 0.4071 |
| bedrock_claude | 998 | 0.7083 | 0.4128 | 0.1845 | 0.2218 |

scored_users openai=998 failed_users=0
scored_users bedrock_micro_nova=996 failed_users=2
scored_users bedrock_qwen=998 failed_users=0
scored_users bedrock_claude=998 failed_users=0

## Post-level

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 19960 | 0.3058 | 0.5533 | 0.3652 | 0.6239 | 0.4607 |
| bedrock_micro_nova | 19920 | 0.3052 | 0.3567 | 0.3131 | 0.9283 | 0.4683 |
| bedrock_qwen | 19960 | 0.3058 | 0.6582 | 0.4450 | 0.4766 | 0.4602 |
| bedrock_claude | 19960 | 0.3058 | 0.7083 | 0.5794 | 0.1686 | 0.2612 |

scored_pairs openai=19960 failed_users=0
scored_pairs bedrock_micro_nova=19920 failed_users=2
scored_pairs bedrock_qwen=19960 failed_users=0
scored_pairs bedrock_claude=19960 failed_users=0

## Party: party_group=democrat

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 598 | 0.5553 | 0.3678 | 0.6154 | 0.4033 |
| bedrock_micro_nova | 597 | 0.3640 | 0.3254 | 0.8615 | 0.4382 |
| bedrock_qwen | 598 | 0.6514 | 0.4661 | 0.4958 | 0.4181 |
| bedrock_claude | 598 | 0.6983 | 0.4225 | 0.1937 | 0.2303 |

scored_users openai=598 failed_users=0
scored_users bedrock_micro_nova=597 failed_users=2
scored_users bedrock_qwen=598 failed_users=0
scored_users bedrock_claude=598 failed_users=0

## Party: party_group=republican

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 400 | 0.5504 | 0.3389 | 0.5558 | 0.3585 |
| bedrock_micro_nova | 399 | 0.3457 | 0.2955 | 0.7876 | 0.3950 |
| bedrock_qwen | 400 | 0.6683 | 0.4439 | 0.4375 | 0.3906 |
| bedrock_claude | 400 | 0.7232 | 0.3983 | 0.1707 | 0.2093 |

scored_users openai=400 failed_users=0
scored_users bedrock_micro_nova=399 failed_users=2
scored_users bedrock_qwen=400 failed_users=0
scored_users bedrock_claude=400 failed_users=0

## Toxicity: sample_low_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 4792 | 0.1592 | 0.6724 | 0.1945 | 0.3368 | 0.2466 |
| bedrock_micro_nova | 4782 | 0.1593 | 0.2673 | 0.1623 | 0.8648 | 0.2733 |
| bedrock_qwen | 4792 | 0.1592 | 0.7990 | 0.2487 | 0.1298 | 0.1705 |
| bedrock_claude | 4792 | 0.1592 | 0.8379 | 0.3333 | 0.0183 | 0.0348 |

scored_pairs openai=4792 failed_users=0
scored_pairs bedrock_micro_nova=4782 failed_users=2
scored_pairs bedrock_qwen=4792 failed_users=0
scored_pairs bedrock_claude=4792 failed_users=0

## Toxicity: sample_middle_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.2775 | 0.5077 | 0.3013 | 0.5872 | 0.3983 |
| bedrock_micro_nova | 9960 | 0.2766 | 0.3265 | 0.2818 | 0.9267 | 0.4322 |
| bedrock_qwen | 9980 | 0.2775 | 0.6400 | 0.3622 | 0.3911 | 0.3761 |
| bedrock_claude | 9980 | 0.2775 | 0.7217 | 0.4934 | 0.1073 | 0.1762 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9960 failed_users=2
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Toxicity: sample_high_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 5188 | 0.4958 | 0.5310 | 0.5187 | 0.7484 | 0.6128 |
| bedrock_micro_nova | 5178 | 0.4948 | 0.4973 | 0.4958 | 0.9489 | 0.6513 |
| bedrock_qwen | 5188 | 0.4958 | 0.5630 | 0.5484 | 0.6715 | 0.6037 |
| bedrock_claude | 5188 | 0.4958 | 0.5628 | 0.6343 | 0.2792 | 0.3877 |

scored_pairs openai=5188 failed_users=0
scored_pairs bedrock_micro_nova=5178 failed_users=2
scored_pairs bedrock_qwen=5188 failed_users=0
scored_pairs bedrock_claude=5188 failed_users=0

## Stance: left

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3086 | 0.5563 | 0.3722 | 0.6373 | 0.4700 |
| bedrock_micro_nova | 9960 | 0.3079 | 0.3606 | 0.3170 | 0.9319 | 0.4730 |
| bedrock_qwen | 9980 | 0.3086 | 0.6612 | 0.4562 | 0.5094 | 0.4814 |
| bedrock_claude | 9980 | 0.3086 | 0.7087 | 0.5991 | 0.1698 | 0.2646 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9960 failed_users=2
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Stance: right

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3030 | 0.5503 | 0.3580 | 0.6101 | 0.4512 |
| bedrock_micro_nova | 9960 | 0.3024 | 0.3527 | 0.3093 | 0.9246 | 0.4635 |
| bedrock_qwen | 9980 | 0.3030 | 0.6551 | 0.4325 | 0.4431 | 0.4378 |
| bedrock_claude | 9980 | 0.3030 | 0.7079 | 0.5604 | 0.1673 | 0.2577 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9960 failed_users=2
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0
