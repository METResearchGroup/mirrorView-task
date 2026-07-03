| type     | ablation             | model_size | model_name   | split | accuracy | precision | recall | f1    | roc_auc | pr_auc |
|:---------|:---------------------|:-----------|:-------------|:------|---------:|----------:|-------:|------:|--------:|-------:|
| one-shot | original             | small      | gpt-5.4-nano | train |    0.690 |     0.519 |  0.443 | 0.478 |   0.678 |  0.491 |
| one-shot | original             | small      | gpt-5.4-nano | test  |    0.686 |     0.510 |  0.485 | 0.497 |   0.695 |  0.515 |
| one-shot | original plus mirror | small      | gpt-5.4-nano | train |    0.682 |     0.504 |  0.308 | 0.382 |   0.627 |  0.448 |
| one-shot | original plus mirror | small      | gpt-5.4-nano | test  |    0.676 |     0.490 |  0.314 | 0.383 |   0.615 |  0.448 |
