# Results from grilling session with AI

Notes from the `/grill-me` session that lock the experiment design.

## Claim

The primary claim is that unanimous keep and unanimous remove sit in clearer, more extreme content regions than strict majority keep and remove, and that disagreement concentrates in middle toxicity posts that are shorter and more arguable.

The secondary claim is that remove looks more like threshold violations than like political disagreement. The secondary claim is tested descriptively with toxicity and stance, and it is not the headline claim.

The method is descriptive only. The work does not run hypothesis tests, and it does not report confidence intervals.

## Cohort

The analysis set is slim linked-fate trials with `n_raters >= 3`.

The four cells are unanimous keep, majority keep, majority remove, and unanimous remove.

Exact ties are excluded, and they are not analyzed.

The cohort stays local to this experiment, and it is not added as a new shared registry dataset.

Expected sizes on the current data are about 1,490, 1,480, 594, and 154.

## Text and joins

Analyses 1 and 3, along with the length and toxicity gradients, use `original_text` only.

Toxicity strata come from `sample_toxicity_type` in `{low, middle, high}`.

Stance comes from stimuli `sampled_stance` in `{left, right}`.

## Analysis 1

Analysis 1 runs the full surface set on original text.

Length and structure metrics include character, word, and sentence counts, average sentence length, and punctuation density.

Readability metrics include Flesch-Kincaid grade and reading ease.

Classifiers come from `shared/textual_features/` and include valence, intergroup, and PRIME. The PRIME family covers prestige, in group, moral, and emotional cues, and the report uses the shared binary `is_prime` label.

Results are reported by cell as descriptive summaries. Continuous metrics follow the same spirit as the existing median length gradient.

## Analysis 2

Analysis 2 turns Stage 1 language model features into word clouds.

Only Stage 1 from the `create_llm_features` lineage is in scope. Embed, cluster, and label stages are out of scope.

Every post in the four cells must be covered. Existing Stage 1 rows are reused for overlapping `message_id` values, and only missing ids are generated through a thin adapter in this experiment. Older experiment outputs are not changed.

The dual text prompt with original and mirror text is kept, so feature extraction stays comparable to reused rows.

Word cloud construction tokenizes `feature_value` across all categories, drops stopwords, punctuation, and low content tokens such as `none` and `in`, counts each token at most once per post, and lightly scrubs meta tokens such as `mirror` and `original`.

The deliverables are four clouds and top N token tables per cell, with N about 30.

## Analysis 3

Analysis 3 builds three tables that cross `sampled_stance` (left or right) with the four cells, one table for each toxicity stratum.

## Out of scope

Out of scope work includes ties, formal inference, `rater_agreement_2026_08_06`, Stages 2 through 4 clustering, a shared catalog majority dataset, and a strategy document writeup.

## Done bar

The done bar is working scripts under this experiment, a rewritten README that matches this design, and `RESULTS.md` plus `outputs/` figures and tables for the analyses above.
