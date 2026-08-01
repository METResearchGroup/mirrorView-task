# LLM-based feature generation

## Problem statement

We want to ask an LLM to generate some plausible features. We're extending the results of `experiments/followup_model_error_analysis_2026_07_15`.

We want to take groups of posts, just like we did there. Perhaps batches of, say, 10 posts that were rated as keep and 10 as remove, and then we'll ask for features. We'll use a similar prompt as in `experiments/followup_model_error_analysis_2026_07_15` but reworded to focus on the slightly different task (rather than including false positive/negatives).

Then we'll take these features and pass to a subsequent LLM call to find thematic commonalities.

Once that's done, we'll take that final list as our substantive experimental results.

## Pipeline

1. Load Study Phase 2 Part 2 results via `shared/data/`.
2. Derive one modal keep/remove label per post (tie → remove).
3. Sample a configurable fraction without replacement and form mixed keep/remove batches.
4. Stage 1: feature generation per batch via `research_tools.llm.runner.run`.
5. Stage 2: thematic commonality synthesis over aggregated stage-1 features.

Outputs are written under `outputs/{timestamp}/` for each stage (metadata plus per-item JSON).

## Smoke test (cheap validation)

Run a live end-to-end sample with **one batch** (10 keep + 10 remove posts). Smoke uses fraction sampling only and must **not** create or overwrite `data/sampled_subset.csv` (that frozen 50% file is owned by the production Step 5 run).

```bash
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
```

Equivalent CLI flags:

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.005 \
  --keep-per-batch 10 \
  --remove-per-batch 10 \
  --seed 42
```

Requires `OPENAI_API_KEY` in the repo-root `.env` (loaded via `research_tools`).

## Approval gate before production run

**Do not start the 50% production run until the user explicitly approves after reviewing Step 4 smoke results.**

After smoke passes and results are reviewed, run the frozen 50% corpus (Step 5). That step persists and reuses `data/sampled_subset.csv` so re-runs do not reshuffle posts. Smoke must not write that file.

## Production run (after explicit approval only)

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.50 \
  --seed 42
```

## Duplicate prevention

Within a run, sampling is without replacement and batching asserts unique `message_id` values across batches.

Across re-runs, `research_tools.llm.runner.run` always creates a new `outputs/{timestamp}/` folder. Avoid double-processing by using a fixed seed (recorded in metadata) and/or `--exclude-ids-from` pointing at a prior run's `metadata.json` or a JSON list of processed message ids.

## CLI flags

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-fraction` | `0.50` | Fraction of modal keep/remove posts to sample |
| `--seed` | `42` | Deterministic sample seed |
| `--keep-per-batch` | `10` | Keep posts per stage-1 batch |
| `--remove-per-batch` | `10` | Remove posts per stage-1 batch |
| `--model` | `gpt-5.4-nano` | Model id |
| `--exclude-ids-from` | unset | Prior `metadata.json` or JSON id list to exclude |
| `--stage1-only` | unset | Run stage 1 only |
| `--stage2-only` | unset | Run stage 2 only (requires `--stage1-dir`) |
