# Experiment 6 results

## Cohort

998 unique prolific_ids from 1000 cohort user rows. Duplicate prolific_ids: 6a1094c7ef643bf92ae4828a, 6a1b6df9270d2d83bc80908f.

## User-level

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.6374 | 0.4327 | 0.5474 | 0.4336 |
| bedrock_micro_nova | 947 | 0.6718 | 0.4436 | 0.3042 | 0.3136 |
| bedrock_qwen | 998 | 0.6357 | 0.4354 | 0.6065 | 0.4605 |

scored_users openai=998 failed_users=0
scored_users bedrock_micro_nova=947 failed_users=51
scored_users bedrock_qwen=998 failed_users=0

## Post-level

| model | n_pairs | baseline remove rate | predicted remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 19960 | 0.3058 | 0.3982 | 0.6374 | 0.4287 | 0.5582 | 0.4849 |
| bedrock_micro_nova | 18940 | 0.3040 | 0.2056 | 0.6718 | 0.4409 | 0.2982 | 0.3558 |
| bedrock_qwen | 19960 | 0.3058 | 0.4464 | 0.6357 | 0.4345 | 0.6343 | 0.5158 |

scored_pairs openai=19960 failed_users=0
scored_pairs bedrock_micro_nova=18940 failed_users=51
scored_pairs bedrock_qwen=19960 failed_users=0

## Party: party_group=democrat

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 598 | 0.6300 | 0.4412 | 0.5839 | 0.4520 |
| bedrock_micro_nova | 566 | 0.6611 | 0.4505 | 0.3204 | 0.3255 |
| bedrock_qwen | 598 | 0.6265 | 0.4430 | 0.6453 | 0.4763 |

scored_users openai=598 failed_users=0
scored_users bedrock_micro_nova=566 failed_users=51
scored_users bedrock_qwen=598 failed_users=0

## Party: party_group=republican

| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 400 | 0.6484 | 0.4199 | 0.4928 | 0.4062 |
| bedrock_micro_nova | 381 | 0.6875 | 0.4333 | 0.2802 | 0.2959 |
| bedrock_qwen | 400 | 0.6495 | 0.4239 | 0.5486 | 0.4369 |

scored_users openai=400 failed_users=0
scored_users bedrock_micro_nova=381 failed_users=51
scored_users bedrock_qwen=400 failed_users=0

## Toxicity: sample_low_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 4792 | 0.1592 | 0.8030 | 0.2377 | 0.1075 | 0.1480 |
| bedrock_micro_nova | 4550 | 0.1569 | 0.8103 | 0.2271 | 0.0868 | 0.1256 |
| bedrock_qwen | 4792 | 0.1592 | 0.7957 | 0.2621 | 0.1560 | 0.1956 |

scored_pairs openai=4792 failed_users=0
scored_pairs bedrock_micro_nova=4550 failed_users=51
scored_pairs bedrock_qwen=4792 failed_users=0

## Toxicity: sample_middle_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.2775 | 0.6085 | 0.3534 | 0.4955 | 0.4126 |
| bedrock_micro_nova | 9470 | 0.2768 | 0.6667 | 0.3403 | 0.2175 | 0.2654 |
| bedrock_qwen | 9980 | 0.2775 | 0.6039 | 0.3632 | 0.5677 | 0.4430 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9470 failed_users=51
scored_pairs bedrock_qwen=9980 failed_users=0

## Toxicity: sample_high_toxicity

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 5188 | 0.4958 | 0.5399 | 0.5249 | 0.7593 | 0.6207 |
| bedrock_micro_nova | 4920 | 0.4923 | 0.5533 | 0.5576 | 0.4480 | 0.4968 |
| bedrock_qwen | 5188 | 0.4958 | 0.5492 | 0.5282 | 0.8480 | 0.6509 |

scored_pairs openai=5188 failed_users=0
scored_pairs bedrock_micro_nova=4920 failed_users=51
scored_pairs bedrock_qwen=5188 failed_users=0

## Stance: left

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3086 | 0.6396 | 0.4366 | 0.5776 | 0.4973 |
| bedrock_micro_nova | 9470 | 0.3073 | 0.6701 | 0.4499 | 0.3302 | 0.3809 |
| bedrock_qwen | 9980 | 0.3086 | 0.6329 | 0.4366 | 0.6532 | 0.5234 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9470 failed_users=51
scored_pairs bedrock_qwen=9980 failed_users=0

## Stance: right

| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 9980 | 0.3030 | 0.6352 | 0.4203 | 0.5384 | 0.4721 |
| bedrock_micro_nova | 9470 | 0.3006 | 0.6734 | 0.4300 | 0.2655 | 0.3283 |
| bedrock_qwen | 9980 | 0.3030 | 0.6386 | 0.4323 | 0.6151 | 0.5077 |

scored_pairs openai=9980 failed_users=0
scored_pairs bedrock_micro_nova=9470 failed_users=51
scored_pairs bedrock_qwen=9980 failed_users=0

## Comparison against experiment 1

Users scored in both experiment 1 and experiment 6 for that model.

| model | n_users | exp1 user F1 | exp6 user F1 | exp1 post F1 | exp6 post F1 | exp1 accuracy | exp6 accuracy | exp1 precision | exp6 precision | exp1 recall | exp6 recall | exp1 pred remove | exp6 pred remove | gold remove | agreement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| openai | 998 | 0.3853 | 0.4336 | 0.4607 | 0.4849 | 0.5533 | 0.6374 | 0.3652 | 0.4287 | 0.6239 | 0.5582 | 0.5224 | 0.3982 | 0.3058 | 0.6683 |
| bedrock_micro_nova | 946 | 0.4194 | 0.3134 | 0.4668 | 0.3557 | 0.3558 | 0.6718 | 0.3118 | 0.4405 | 0.9285 | 0.2982 | 0.9045 | 0.2057 | 0.3038 | 0.2821 |
| bedrock_qwen | 998 | 0.4071 | 0.4605 | 0.4602 | 0.5158 | 0.6582 | 0.6357 | 0.4450 | 0.4345 | 0.4766 | 0.6343 | 0.3275 | 0.4464 | 0.3058 | 0.7425 |

## Within-user variance of per-pair correctness

Population variance of per-pair correctness on the intersection users.

| model | experiment | mean | median | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| openai | 1 | 0.2137 | 0.2275 | 0.2100 | 0.2475 |
| openai | 6 | 0.2153 | 0.2275 | 0.1875 | 0.2475 |
| bedrock_micro_nova | 1 | 0.1850 | 0.2100 | 0.1600 | 0.2400 |
| bedrock_micro_nova | 6 | 0.1973 | 0.2100 | 0.1600 | 0.2400 |
| bedrock_qwen | 1 | 0.2067 | 0.2275 | 0.1875 | 0.2400 |
| bedrock_qwen | 6 | 0.2158 | 0.2275 | 0.1875 | 0.2475 |
