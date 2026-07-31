# LLM-based feature generation

## Problem statement

We want to ask an LLM to generate some plausible features. We're extending the results of `experiments/followup_model_error_analysis_2026_07_15`.

We want to take groups of posts, just like we did there. Perhaps batches of, say, 10 posts that were rated as keep and 10 as remove, and then we'll ask for features. We'll use a similar prompt as in `experiments/followup_model_error_analysis_2026_07_15` but reworded to focus on the slightly different task (rather than including false positive/negatives).

Then we'll take these features and pass to a subsequent LLM call to find thematic commonalities.

Once that's done, we'll take that final list as our substantive experimental results.
