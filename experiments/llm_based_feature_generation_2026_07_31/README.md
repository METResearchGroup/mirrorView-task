# LLM-based feature generation

## Problem statement

We want to ask an LLM to generate some plausible features. We're extending the results of `experiments/followup_model_error_analysis_2026_07_15`.

We want to take groups of posts, just like we did there. Perhaps batches of, say, 10 posts that were rated as keep and 10 as remove, and then we'll ask for features. We'll use a similar prompt as in `experiments/followup_model_error_analysis_2026_07_15` but reworded to focus on the slightly different task (rather than including false positive/negatives).

Then we'll take these features and pass to a subsequent LLM call to find thematic commonalities.

Once that's done, we'll take that final list as our substantive experimental results.

## Data and sampling

- Posts: Study 2 human keep/remove labels via `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` (`load_training_dataframe`).
- Target corpus: **50%** of posts. Start with a **1% pilot**.
- Batches: ~10 keep + ~10 remove per stage-1 call.
- Model: `gpt-5.4-nano`.

## Duplicate prevention

Within a run:

- Sampling is without replacement (stratified by keep/remove).
- Each `message_id` appears in at most one batch; uniqueness is asserted before the LLM runner is called.

Across re-runs:

- `research_tools.llm.runner.run` always writes a **new** `outputs/{timestamp}/` folder (no resume/skip of already-written items).
- Avoid accidental double-processing by using a fixed `--seed` (ids recorded in stage-1 `metadata.json` → `run_metadata.message_ids`) and/or `--exclude-ids-from` pointing at a prior metadata file or a JSON list of ids.

## How to run

```bash
# End-to-end smoke (1 keep + 1 remove → stage1 + stage2; live LLM)
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py

# 1% pilot (default)
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.01 --seed 42

# 50% target (gated — only after pilot + cost approval)
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.50 --seed 42
```

Requires `OPENAI_API_KEY` in the repo-root `.env` (loaded by `research_tools`).

Outputs land under `experiments/llm_based_feature_generation_2026_07_31/outputs/{timestamp}/`.
