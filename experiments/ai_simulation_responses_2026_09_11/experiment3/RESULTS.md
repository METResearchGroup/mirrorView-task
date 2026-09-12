# Experiment 3 results

## Cohort

998 unique prolific_ids from 1000 cohort user rows. Duplicate prolific_ids: 6a1094c7ef643bf92ae4828a, 6a1b6df9270d2d83bc80908f.

## User-level

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.6117 | 0.4018 | 0.5925 | 0.4242 |
| bedrock_micro_nova | 997 | 0.3806 | 0.3160 | 0.8390 | 0.4255 |
| bedrock_qwen | 998 | 0.6886 | 0.4874 | 0.4636 | 0.4227 |
| bedrock_claude | 998 | 0.7325 | 0.5148 | 0.2560 | 0.3054 |

scored_users openai=998 failed_users=0
scored_users bedrock_micro_nova=997 failed_users=1
scored_users bedrock_qwen=998 failed_users=0
scored_users bedrock_claude=998 failed_users=0

## Post-level

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 19960 | 0.3058 | 0.6117 | 0.4138 | 0.6473 | 0.5048 |
| bedrock_micro_nova | 19940 | 0.3058 | 0.3806 | 0.3241 | 0.9451 | 0.4827 |
| bedrock_qwen | 19960 | 0.3058 | 0.6886 | 0.4904 | 0.4664 | 0.4781 |
| bedrock_claude | 19960 | 0.3058 | 0.7325 | 0.6673 | 0.2497 | 0.3634 |

scored_pairs openai=19960 failed_users=0
scored_pairs bedrock_micro_nova=19940 failed_users=1
scored_pairs bedrock_qwen=19960 failed_users=0
scored_pairs bedrock_claude=19960 failed_users=0

## Party: party_group=democrat

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 598 | 0.6145 | 0.4162 | 0.6169 | 0.4424 |
| bedrock_micro_nova | 597 | 0.3902 | 0.3276 | 0.8615 | 0.4413 |
| bedrock_qwen | 598 | 0.6814 | 0.4968 | 0.4806 | 0.4318 |
| bedrock_claude | 598 | 0.7248 | 0.5244 | 0.2727 | 0.3193 |

scored_users openai=598 failed_users=0
scored_users bedrock_micro_nova=597 failed_users=1
scored_users bedrock_qwen=598 failed_users=0
scored_users bedrock_claude=598 failed_users=0

## Party: party_group=republican

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 400 | 0.6075 | 0.3803 | 0.5561 | 0.3971 |
| bedrock_micro_nova | 400 | 0.3664 | 0.2987 | 0.8054 | 0.4019 |
| bedrock_qwen | 400 | 0.6995 | 0.4735 | 0.4381 | 0.4091 |
| bedrock_claude | 400 | 0.7439 | 0.5005 | 0.2310 | 0.2846 |

scored_users openai=400 failed_users=0
scored_users bedrock_micro_nova=400 failed_users=1
scored_users bedrock_qwen=400 failed_users=0
scored_users bedrock_claude=400 failed_users=0

## Toxicity: sample_low_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 4792 | 0.1592 | 0.7379 | 0.2600 | 0.3499 | 0.2983 |
| bedrock_micro_nova | 4788 | 0.1591 | 0.2826 | 0.1715 | 0.9160 | 0.2890 |
| bedrock_qwen | 4792 | 0.1592 | 0.8130 | 0.2915 | 0.1219 | 0.1719 |
| bedrock_claude | 4792 | 0.1592 | 0.8402 | 0.4634 | 0.0249 | 0.0473 |

scored_pairs openai=4792 failed_users=0
scored_pairs bedrock_micro_nova=4788 failed_users=1
scored_pairs bedrock_qwen=4792 failed_users=0
scored_pairs bedrock_claude=4792 failed_users=0

## Toxicity: sample_middle_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.2775 | 0.5734 | 0.3465 | 0.6067 | 0.4411 |
| bedrock_micro_nova | 9970 | 0.2771 | 0.3501 | 0.2912 | 0.9377 | 0.4443 |
| bedrock_qwen | 9980 | 0.2775 | 0.6754 | 0.4059 | 0.3669 | 0.3854 |
| bedrock_claude | 9980 | 0.2775 | 0.7353 | 0.5859 | 0.1564 | 0.2469 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9970 failed_users=1
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Toxicity: sample_high_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 5188 | 0.4958 | 0.5686 | 0.5455 | 0.7792 | 0.6417 |
| bedrock_micro_nova | 5182 | 0.4963 | 0.5301 | 0.5142 | 0.9615 | 0.6701 |
| bedrock_qwen | 5188 | 0.4958 | 0.5993 | 0.5826 | 0.6757 | 0.6257 |
| bedrock_claude | 5188 | 0.4958 | 0.6276 | 0.7128 | 0.4168 | 0.5260 |

scored_pairs openai=5188 failed_users=0
scored_pairs bedrock_micro_nova=5182 failed_users=1
scored_pairs bedrock_qwen=5188 failed_users=0
scored_pairs bedrock_claude=5188 failed_users=0

## Stance: left

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3086 | 0.6185 | 0.4246 | 0.6649 | 0.5183 |
| bedrock_micro_nova | 9970 | 0.3085 | 0.3856 | 0.3283 | 0.9483 | 0.4878 |
| bedrock_qwen | 9980 | 0.3086 | 0.6926 | 0.5020 | 0.4990 | 0.5005 |
| bedrock_claude | 9980 | 0.3086 | 0.7406 | 0.7086 | 0.2708 | 0.3918 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9970 failed_users=1
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0

## Stance: right

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3030 | 0.6048 | 0.4027 | 0.6293 | 0.4911 |
| bedrock_micro_nova | 9970 | 0.3030 | 0.3757 | 0.3199 | 0.9417 | 0.4776 |
| bedrock_qwen | 9980 | 0.3030 | 0.6847 | 0.4776 | 0.4332 | 0.4543 |
| bedrock_claude | 9980 | 0.3030 | 0.7243 | 0.6233 | 0.2282 | 0.3341 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9970 failed_users=1
scored_pairs bedrock_qwen=9980 failed_users=0
scored_pairs bedrock_claude=9980 failed_users=0
