# Part 3 LoRA cross-eval keep/remove results

- Model: `Qwen/Qwen3.5-4B`
- Seed: 1
- Positive class: remove

## Remove-F1 matrix (95% bootstrap CI)

| Arm | unanimous test | modal test |
| --- | --- | --- |
| zero-shot | 0.8079 [0.7444, 0.8630] | 0.7342 [0.7140, 0.7538] |
| Experiment 1 | 0.9333 [0.8889, 0.9704] | 0.7192 [0.6935, 0.7427] |
| Experiment 2 | 0.9195 [0.8721, 0.9561] | 0.7746 [0.7533, 0.7952] |
| Experiment 3 | 0.9059 [0.8555, 0.9451] | 0.7446 [0.7224, 0.7657] |

## Full metrics

| arm | test_set | n | n_remove | accuracy | precision | recall | f1 | f1_ci_low | f1_ci_high | invalid_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zero-shot | test_unanimous | 168 | 84 | 0.7679 | 0.6891 | 0.9762 | 0.8079 | 0.7444 | 0.8630 | 0.0000 |
| zero-shot | test_modal | 1922 | 961 | 0.6644 | 0.6078 | 0.9272 | 0.7342 | 0.7140 | 0.7538 | 0.0000 |
| experiment1_unanimous | test_unanimous | 168 | 84 | 0.9345 | 0.9506 | 0.9167 | 0.9333 | 0.8889 | 0.9704 | 0.0000 |
| experiment1_unanimous | test_modal | 1922 | 961 | 0.7497 | 0.8191 | 0.6410 | 0.7192 | 0.6935 | 0.7427 | 0.0000 |
| experiment2_modal | test_unanimous | 168 | 84 | 0.9167 | 0.8889 | 0.9524 | 0.9195 | 0.8721 | 0.9561 | 0.0000 |
| experiment2_modal | test_modal | 1922 | 961 | 0.7768 | 0.7824 | 0.7669 | 0.7746 | 0.7533 | 0.7952 | 0.0000 |
| experiment3_modal_size_matched | test_unanimous | 168 | 84 | 0.9048 | 0.8953 | 0.9167 | 0.9059 | 0.8555 | 0.9451 | 0.0000 |
| experiment3_modal_size_matched | test_modal | 1922 | 961 | 0.7466 | 0.7505 | 0.7388 | 0.7446 | 0.7224 | 0.7657 | 0.0000 |

## Split counts

| Split | n | n_remove | n_keep |
| --- | --- | --- | --- |
| modal pool posts | 20000 | — | — |
| unanimous-min3 posts | 5715 | — | — |
| Experiment 1 train | 702 | — | — |
| Experiment 2 train | 7686 | — | — |
| Experiment 3 train | 702 | — | — |
| test_unanimous | 168 | 84 | 84 |
| test_modal | 1922 | 961 | 961 |

## Summary

The highest remove-F1 on the Part 3 balanced test sets is Experiment 1 on the unanimous test at 0.9333 [0.8889, 0.9704]. All arms had zero invalid generations.

## Part 2 reference (different base model: `Qwen/Qwen3-4B-Instruct-2507`)

These Part 2 test remove-F1 values use a different base model and are not comparable to Part 3.

| Test set | Arm | remove-F1 |
| --- | --- | --- |
| unanimous | baseline | 0.7407 |
| unanimous | fine-tuned | 0.9688 |
| modal | baseline | 0.7210 |
| modal | fine-tuned | 0.6962 |
