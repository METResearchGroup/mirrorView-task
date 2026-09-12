# Experiment 2 results

## Cohort

998 unique prolific_ids from 1000 cohort user rows. Duplicate prolific_ids: 6a1094c7ef643bf92ae4828a, 6a1b6df9270d2d83bc80908f.

## User-level

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.5504 | 0.3572 | 0.5876 | 0.3858 |
| bedrock_micro_nova | 998 | 0.3497 | 0.3145 | 0.8421 | 0.4234 |
| bedrock_qwen | 998 | 0.6429 | 0.4406 | 0.5022 | 0.4157 |
| bedrock_claude | 998 | 0.7119 | 0.4911 | 0.2301 | 0.2730 |

scored_users openai=998 failed_users=0
scored_users bedrock_micro_nova=998 failed_users=0
scored_users bedrock_qwen=998 failed_users=0
scored_users bedrock_claude=998 failed_users=0

## Post-level

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 19960 | 0.3058 | 0.5504 | 0.3640 | 0.6296 | 0.4613 |
| bedrock_micro_nova | 19960 | 0.3058 | 0.3497 | 0.3123 | 0.9368 | 0.4684 |
| bedrock_qwen | 19960 | 0.3058 | 0.6429 | 0.4302 | 0.5161 | 0.4692 |
| bedrock_claude | 19960 | 0.3058 | 0.7119 | 0.5784 | 0.2140 | 0.3124 |

scored_pairs openai=19960 failed_users=0
scored_pairs bedrock_micro_nova=19960 failed_users=0
scored_pairs bedrock_qwen=19960 failed_users=0
scored_pairs bedrock_claude=19960 failed_users=0

## Party: party_group=democrat

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 598 | 0.5462 | 0.3579 | 0.6163 | 0.3978 |
| bedrock_micro_nova | 598 | 0.3568 | 0.3272 | 0.8643 | 0.4370 |
| bedrock_qwen | 598 | 0.6390 | 0.4501 | 0.5192 | 0.4256 |
| bedrock_claude | 598 | 0.7007 | 0.4921 | 0.2380 | 0.2780 |

scored_users openai=598 failed_users=0
scored_users bedrock_micro_nova=598 failed_users=0
scored_users bedrock_qwen=598 failed_users=0
scored_users bedrock_claude=598 failed_users=0

## Party: party_group=republican

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 400 | 0.5565 | 0.3562 | 0.5446 | 0.3680 |
| bedrock_micro_nova | 400 | 0.3392 | 0.2955 | 0.8090 | 0.4032 |
| bedrock_qwen | 400 | 0.6489 | 0.4263 | 0.4769 | 0.4008 |
| bedrock_claude | 400 | 0.7288 | 0.4897 | 0.2183 | 0.2654 |

scored_users openai=400 failed_users=0
scored_users bedrock_micro_nova=400 failed_users=0
scored_users bedrock_qwen=400 failed_users=0
scored_users bedrock_claude=400 failed_users=0

## Toxicity: sample_low_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 4792 | 0.1592 | 0.6709 | 0.2003 | 0.3565 | 0.2565 |
| bedrock_micro_nova | 4792 | 0.1592 | 0.2506 | 0.1633 | 0.8991 | 0.2764 |
| bedrock_qwen | 4792 | 0.1592 | 0.7773 | 0.2206 | 0.1573 | 0.1836 |
| bedrock_claude | 4792 | 0.1592 | 0.8374 | 0.3182 | 0.0183 | 0.0347 |

scored_pairs openai=4792 failed_users=0
scored_pairs bedrock_micro_nova=4792 failed_users=0
scored_pairs bedrock_qwen=4792 failed_users=0
scored_pairs bedrock_claude=4792 failed_users=0

## Toxicity: sample_middle_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.2775 | 0.5043 | 0.3004 | 0.5919 | 0.3985 |
| bedrock_micro_nova | 9980 | 0.2775 | 0.3194 | 0.2810 | 0.9317 | 0.4317 |
| bedrock_qwen | 9980 | 0.2775 | 0.6200 | 0.3500 | 0.4312 | 0.3864 |
| bedrock_claude | 9980 | 0.2775 | 0.7211 | 0.4910 | 0.1376 | 0.2150 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Toxicity: sample_high_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 5188 | 0.4958 | 0.5276 | 0.5162 | 0.7512 | 0.6119 |
| bedrock_micro_nova | 5188 | 0.4958 | 0.4996 | 0.4976 | 0.9533 | 0.6539 |
| bedrock_qwen | 5188 | 0.4958 | 0.5628 | 0.5451 | 0.7138 | 0.6182 |
| bedrock_claude | 5188 | 0.4958 | 0.5783 | 0.6335 | 0.3542 | 0.4544 |

scored_pairs openai=5188 failed_users=0
scored_pairs bedrock_micro_nova=5188 failed_users=0
scored_pairs bedrock_qwen=5188 failed_users=0
scored_pairs bedrock_claude=5188 failed_users=0

## Stance: left

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3086 | 0.5510 | 0.3696 | 0.6445 | 0.4698 |
| bedrock_micro_nova | 9980 | 0.3086 | 0.3533 | 0.3159 | 0.9396 | 0.4728 |
| bedrock_qwen | 9980 | 0.3086 | 0.6456 | 0.4404 | 0.5481 | 0.4884 |
| bedrock_claude | 9980 | 0.3086 | 0.7144 | 0.6005 | 0.2231 | 0.3253 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Stance: right

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3030 | 0.5497 | 0.3583 | 0.6144 | 0.4526 |
| bedrock_micro_nova | 9980 | 0.3030 | 0.3462 | 0.3087 | 0.9339 | 0.4640 |
| bedrock_qwen | 9980 | 0.3030 | 0.6403 | 0.4189 | 0.4835 | 0.4489 |
| bedrock_claude | 9980 | 0.3030 | 0.7094 | 0.5557 | 0.2047 | 0.2992 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9980 failed_users=0
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0
