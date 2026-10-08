# Train and test on the entire split-label tables

Training uses every row of `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Testing uses every row of `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Every row in both tables has five labelers and 1, 2, 3, or 4 remove votes. The predictors are the 30 binary columns in `post_feature_labels.parquet`.

The train table has 14,562 rows, 7,281 keep and 7,281 remove. The test table has 9,941 rows, 7,281 keep and 2,660 remove. The upsampled table already contains every regular post, so all 9,941 test posts also appear in training.

## Logistic regression

The positive class is remove. A row is predicted remove when the remove probability is at least 0.5.

| Split | Rows | Accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 14,562 | 0.6761 | 0.6669 | 0.7035 | 0.6847 |
| Test | 9,941 | 0.6627 | 0.4217 | 0.7011 | 0.5266 |

A prediction that always says keep is correct on 7,281 of the 9,941 test posts, so its accuracy is 0.7324. Its remove F1 is 0. The fitted test accuracy is 0.6627, and the fitted test F1 is 0.5266.

## Linear regression

The target is `n_remove / n_raters`. MAE, RMSE, and R^2 use predictions limited to the range 0 to 1. `outside` counts raw predictions below 0 or above 1.

| Split | Rows | MAE | RMSE | R^2 | Outside 0 to 1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 14,562 | 0.1598 | 0.1901 | 0.2135 | 0 of 14,562 |
| Test | 9,941 | 0.1612 | 0.1902 | 0.0541 | 0 of 9,941 |

## Largest logistic coefficients

| Feature | Name | Coefficient |
| --- | --- | ---: |
| `intercept` | Intercept | -0.8984 |
| `is_dense_profanity_and_vulgar_insults` | Dense Profanity and Vulgar Insults | 1.1976 |
| `is_hostile_outrage_venting` | Hostile Outrage Venting | 0.4992 |
| `is_brief_slogan_like_insult_attacks` | Brief Slogan-Like Insult Attacks | 0.4561 |
| `is_punitive_blanket_condemnation_of_political_opponents` | Punitive Blanket Condemnation of Political Opponents | 0.4535 |
| `is_limited_profanity_within_argument` | Limited Profanity Within Argument | 0.3743 |
| `is_escalatory_partisan_hostility` | Escalatory Partisan Hostility | 0.3247 |
| `is_reasoned_political_policy_persuasion` | Reasoned Political Policy Persuasion | 0.2935 |
| `is_blanket_demonization_of_political_opponents` | Blanket Demonization of Political Opponents | 0.2874 |
| `is_policy_advocacy_and_tradeoff_arguments` | Policy Advocacy and Tradeoff Arguments | -0.2638 |
| `is_partisan_mockery_and_taunting` | Partisan Mockery and Taunting | 0.2345 |

## Largest linear coefficients

| Feature | Name | Coefficient |
| --- | --- | ---: |
| `intercept` | Intercept | 0.3853 |
| `is_dense_profanity_and_vulgar_insults` | Dense Profanity and Vulgar Insults | 0.0977 |
| `is_hostile_outrage_venting` | Hostile Outrage Venting | 0.0570 |
| `is_punitive_blanket_condemnation_of_political_opponents` | Punitive Blanket Condemnation of Political Opponents | 0.0438 |
| `is_brief_slogan_like_insult_attacks` | Brief Slogan-Like Insult Attacks | 0.0427 |
| `is_limited_profanity_within_argument` | Limited Profanity Within Argument | 0.0347 |
| `is_escalatory_partisan_hostility` | Escalatory Partisan Hostility | 0.0307 |
| `is_blanket_demonization_of_political_opponents` | Blanket Demonization of Political Opponents | 0.0292 |
| `is_sweeping_unsubstantiated_political_accusations` | Sweeping Unsubstantiated Political Accusations | -0.0251 |
| `is_substantive_policy_and_institutional_claims` | Substantive Policy and Institutional Claims | -0.0249 |
| `is_reasoned_political_policy_persuasion` | Reasoned Political Policy Persuasion | 0.0242 |
