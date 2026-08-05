# LLM prompt engineering

## Purpose

We did a few experiments in [this folder](../create_llm_features_2026_08_05/) to uncover features in posts that were kept vs. posts that were removed. This allowed us to compile a [list of criteria](KEEP_REMOVE_FEATURES.md) often shared in posts that were kept vs. removed.

We now want to run an LLM classifier.

## Approach

We do the following:

- Grab the posts from `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` in `shared/data/registry.py`.
- Take a subset of 500 posts. Store as subset_labels.csv (we add this to Git as well).
- Run two sets of prompts (we have a single runner that can run both versions of the prompts) across all 500 posts.
- Record the labels.
- Record the results (we track accuracy, F1, precision, and recall).
- Report a table, in RESULTS.md, with the metrics. These are two-row tables, one row for the control and one row for the prompt-tuned version, reporting the accuracy, F1, precision, and recall.

We use the same Pydantic model in `shared/schemas.py` for our response class.

We use `gpt5.4-nano` here, as in our other experiments.
