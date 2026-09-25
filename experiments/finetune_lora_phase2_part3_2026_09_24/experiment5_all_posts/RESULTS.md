# Experiment 5: all-posts inference scores

All-posts scores use the modal keep/remove label as gold. The all_posts and train slices include posts each model trained on, so they are not held-out evaluations.

## Overall slices

| model | slice | n | n_remove | accuracy | precision | recall | f1 | invalid_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| unanimous_model | all_posts | 20000 | 4804 | 0.8021 | 0.5811 | 0.6309 | 0.6050 | 0.0000 |
| unanimous_model | train | 15999 | 3843 | 0.8001 | 0.5770 | 0.6287 | 0.6017 | 0.0000 |
| unanimous_model | test | 4001 | 961 | 0.8100 | 0.5977 | 0.6400 | 0.6181 | 0.0000 |
| unanimous_model | unanimous_posts | 5715 | 435 | 0.9584 | 0.6495 | 0.9839 | 0.7824 | 0.0000 |
| modal_model | all_posts | 20000 | 4804 | 0.7903 | 0.5436 | 0.7910 | 0.6443 | 0.0000 |
| modal_model | train | 15999 | 3843 | 0.7941 | 0.5492 | 0.7970 | 0.6503 | 0.0000 |
| modal_model | test | 4001 | 961 | 0.7748 | 0.5212 | 0.7669 | 0.6206 | 0.0000 |
| modal_model | unanimous_posts | 5715 | 435 | 0.9263 | 0.5086 | 0.9563 | 0.6640 | 0.0000 |

## Five-rater posts by remove-vote count

| model | n_remove | n | n_label_remove | accuracy | precision | recall | f1 | invalid_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| unanimous_model | 0 | 3962 | 0 | 0.9611 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| unanimous_model | 1 | 4511 | 0 | 0.8725 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| unanimous_model | 2 | 3277 | 0 | 0.7052 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| unanimous_model | 3 | 1881 | 1881 | 0.5428 | 1.0000 | 0.5428 | 0.7037 | 0.0000 |
| unanimous_model | 4 | 934 | 934 | 0.7612 | 1.0000 | 0.7612 | 0.8644 | 0.0000 |
| unanimous_model | 5 | 319 | 319 | 0.9875 | 1.0000 | 0.9875 | 0.9937 | 0.0000 |
| modal_model | 0 | 3962 | 0 | 0.9346 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modal_model | 1 | 4511 | 0 | 0.8014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modal_model | 2 | 3277 | 0 | 0.5981 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modal_model | 3 | 1881 | 1881 | 0.7363 | 1.0000 | 0.7363 | 0.8481 | 0.0000 |
| modal_model | 4 | 934 | 934 | 0.9133 | 1.0000 | 0.9133 | 0.9547 | 0.0000 |
| modal_model | 5 | 319 | 319 | 0.9530 | 1.0000 | 0.9530 | 0.9759 | 0.0000 |
