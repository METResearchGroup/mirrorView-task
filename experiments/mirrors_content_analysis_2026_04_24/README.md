# Mirrors content analysis

Set of basic exploratory analyses for the mirrors.

## Steps

1. Run `dataloader.py`. Get the latest `mirrorview_pilot_trial_data_{timestamp}.csv` file, processing the latest pilot data into a curated form.
2. Run the analyses. Perhaps each of these analyses can be their own subagent and set of scripts?

I'm thinking a setup like this.

```bash
experiments/mirrors_content_analysis_2026-04-24/ # keep this here for now while it's experimental.
  analysis/
    length_compression_analysis.py # exposes run_analysis() function.
    readability.py
    ...
  run_analysis.py # takes as CLI args which analyses to run (user could do a drop-down choice of which ones to run)
  outputs/
    {timestamp}/ # based on the timestamp from run_analysis.py, the analysis/ modules should only be run by run_analysis.py
      length_compression_analysis.csv # could also output .jsonl as well, if we want something more flexible. Can emit "name", "description", and "value" for given measures.
      readability.csv
      ...
      metadata.json # which data file was run, the run timestamp (based on the run for run_analysis.py)
```

The setup for a lot of the analysis I think can be something like this:

```bash
load data -> for all texts, run all analysis functions -> groupby + split across condition x party group -> generate final artifact -> show results -> create visualizations -> save artifact
```

## Analysis 1: Basic length measures

- Number of chars/words/sentences
- Average sentence length
- Punctuation density

### (Analysis 1) Questions to answer

- Aggregate analysis: are mirrored texts systematically longer, shorter, or denser?
- Pairwise analysis: basic stats (ratio, absolute difference). Subtract the metrics between the mirror and regular texts and just plot them.
- Keep/remove decision: test whether longer or more compressed mirrors are more likely to be removed.

## Analysis 2: Readability/complexity

- Flesh-Kincaid (basic readability measure)

### (Analysis 2) Questions to answer

- Aggregate analysis: do mirrored texts become simpler or more formal?
- Pairwise: any change in readability from the bsae to mirror text?
- Keep/remove decision: does more complex or simplified rhetoric get removed more often?

## Analysis 3: Sentiment / Toxicity

- Analyses to run:
  - Basic sentiment
  - VADER
  - Perspective API

## Analysis 4: Moralized

Moralized words (e.g., "rights", "freedom", etc)

Can use Billy's PRIME classifier here. Or can just do a simple LLM-based approach (like what I did before).

## Analysis 5: Absolutism/certainty/hedging

- absolutist language (e.g., "always", "never")

## Analysis 6: Identity-group and outgroup references

Can use the same intergroup LLM classifier from the Bluesky project.

## Analysis 7: Topics

## Analysis 8: Embedding similarity
