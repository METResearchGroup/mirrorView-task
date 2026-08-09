# Unanimous vs majority labels (2026-08-08)

In Study Phase 2 Part 2, linked-fate raters give each post a keep or remove label. A post can get that label when every rater agrees, and it can get the same label when only a strict majority agrees. The experiment asks whether those two cases differ in measurable ways.

The locked design is in [`GRILL.md`](./GRILL.md). The descriptive findings are in [`RESULTS.md`](./RESULTS.md).

## Claims

The primary claim is that unanimous keep and unanimous remove sit at clearer extremes of content, while strict majority keep and remove sit more in the middle on toxicity and length and look more arguable.

The secondary claim is that heavy remove looks more like high toxicity than like a left versus right political split. The secondary claim is descriptive only, and it is tested with toxicity strata and stance tables.

The method is descriptive only. The work does not run hypothesis tests, and it does not report confidence intervals.

## Cohort

The analysis set is linked-fate trials with at least three raters. Posts fall into four cells, with the expected sizes on the current data shown below.

| Cell | Expected n (current data) |
| ---- | ------------------------: |
| `unanimous_keep` | 1,490 |
| `majority_keep` | 1,480 |
| `majority_remove` | 594 |
| `unanimous_remove` | 154 |

Exact ties are dropped, and they are not analyzed. The cohort file stays inside this experiment directory, and it is not added as a new shared registry dataset.

The cohort path is `outputs/cohort/four_cell_cohort.csv`.

## Text and joins

Analyses 1 and 3, along with the length and toxicity summaries, use `original_text` only.

Toxicity strata come from `sample_toxicity_type`, which takes values in `{low, middle, high}`.

Stance comes from the stimuli field `sampled_stance`, which takes values in `{left, right}`.

## Analysis 1

Analysis 1 computes surface metrics and classifiers on original text, then summarizes them by cell. The locked list is:

- Length and structure, including character, word, and sentence counts, average sentence length, and punctuation density
- Readability, including Flesch-Kincaid grade and reading ease
- Classifiers from `shared/textual_features/`, including valence (`is_positive`), intergroup (`is_intergroup`), and PRIME as the shared binary `is_prime` label rather than four separate cue columns

The outputs are `outputs/analysis1/per_post_features.csv` and `outputs/analysis1/cell_summary.csv`.

## Analysis 2

Analysis 2 uses Stage 1 language model features only. It does not run embed, cluster, or label stages.

Every post in the four cells needs a Stage 1 feature set. When a `message_id` already has Stage 1 rows under `experiments/create_llm_features_2026_08_05/`, those rows are reused. Missing ids are generated with the dual text prompt that includes original and mirror text, so new rows stay comparable to reused rows. New files are written only under this experiment, and the older experiment outputs tree is not changed.

Token counting for the word clouds follows these steps:

1. Split each `feature_value` on non letter characters and lowercase the tokens.
2. Drop stopwords, single character tokens, low content tokens, and meta tokens such as `mirror` and `original`.
3. Count each remaining token at most once per post inside each cell.
4. Keep the top 30 tokens by that post count.

The outputs are:

- `outputs/analysis2/coverage.json`
- `outputs/analysis2/merged_stage1_features.jsonl`
- `outputs/analysis2/top_tokens_by_cell.csv`
- `outputs/analysis2/wordcloud_<cell>.png` for each of the four cells

## Analysis 3

Analysis 3 builds three tables of stance by cell, one table for each toxicity stratum. Each table crosses `sampled_stance` (left or right) with the four cells.

The outputs are `outputs/analysis3/stance_by_cell_{low,middle,high}_toxicity.csv` and `outputs/analysis3/stance_by_cell_all_strata.csv`.

## How to run

From the repo root, run:

```bash
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py
PYTHONPATH=. uv run --with wordcloud python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py
```

Analysis 2 feature generation needs an OpenAI API key in the environment, using the same path as other language model experiment scripts.

## Out of scope

The following work is out of scope for this experiment:

- Analyzing exact ties
- Formal statistical tests or confidence intervals
- Work under `experiments/rater_agreement_2026_08_06/`
- Stages 2 through 4 of `experiments/create_llm_features_2026_08_05/` (embed, cluster, and label)
- New shared transformed catalog entries
- A strategy document writeup
