# Experiment 5 setup

After experiments 1 through 4 finish labeling and scoring, this step ranks false-negative posts, false-positive posts, and lowest-F1 users. It reads existing labels and cohort fields only.

## Inputs

Sixteen `final.parquet` files under `../experiment1` through `../experiment4/outputs/{model}/`, plus shared cohort parquet.

## Outputs

`outputs/false_negative_posts.csv`, `outputs/false_positive_posts.csv`, and `outputs/lowest_f1_users.csv`, plus `RESULTS.md`.
