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

### (Analysis 1) Findings

- Run command: `PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis.py`

- Aggregate trend (answer to Q1): mirrored texts are systematically longer but slightly less punctuation-dense.
  - Original overall means: `char_count=204.2`, `word_count=36.02`, `sentence_count=2.727`, `avg_sentence_length=16.49`, `punctuation_density=0.03054`.
  - Mirror overall means: `char_count=235.1`, `word_count=39.16`, `sentence_count=2.714`, `avg_sentence_length=17.83`, `punctuation_density=0.02835`.

- Pairwise trend (answer to Q2): mirrors mostly expand through longer sentences, not more sentences.
  - Mean ratios (`mirror / original`): `char=1.153`, `word=1.092`, `sentence=1.015`, `avg_sentence_length=1.111`, `punctuation_density=0.963`.
  - Mean deltas (`mirror - original`): `char=+31.27`, `word=+3.18`, `sentence=-0.013`, `avg_sentence_length=+1.37`, `punctuation_density=-0.0021`.
  - This pattern is stable by party and condition (`ratio_char` ~= `1.152`-`1.156`; `ratio_word` ~= `1.091`-`1.095`).

- Keep/remove trend (answer to Q3): longer and more expanded mirrors are modestly more likely to be kept (not removed).
  - All rows: keep vs remove `mirror_char_count` = `237.8` vs `229.6`; `ratio_char_count` = `1.159` vs `1.142`; `ratio_word_count` = `1.095` vs `1.086`.
  - Keep rate increases across expansion quartiles:
    - `ratio_char_count` quartiles (Q1->Q4): `0.6497`, `0.6540`, `0.6722`, `0.7042`
    - `ratio_word_count` quartiles (Q1->Q4): `0.6607`, `0.6592`, `0.6731`, `0.6869`
  - Effects are small but consistent (point-biserial correlations with keep are positive for length/ratio metrics, near zero for punctuation density).

## Analysis 2: Readability/complexity

- Flesch-Kincaid Grade Level (`flesch_kincaid_grade`)
- Flesch Reading Ease (`flesch_reading_ease`)
- Implementation uses spaCy sentence/token boundaries and explicit metric formulas in `analysis/readability_complexity_analysis.py`.

### (Analysis 2) Questions to answer

- Aggregate analysis: do mirrored texts become simpler or more formal?
- Pairwise: any change in readability from the base to mirror text?
- Keep/remove decision: does more complex or simplified rhetoric get removed more often?

### (Analysis 2) Findings

- Run command: `PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis.py`

- Aggregate trend (answer to Q1): mirrored texts become substantially more complex/read less easily.
  - Original overall means: `flesch_kincaid_grade=8.814`, `flesch_reading_ease=61.38`.
  - Mirror overall means: `flesch_kincaid_grade=10.72`, `flesch_reading_ease=49.94`.
  - Interpretation guide: higher `flesch_kincaid_grade` = more complex; lower `flesch_reading_ease` = more complex.

- Pairwise trend (answer to Q2): mirrors shift toward higher grade-level complexity and lower reading ease.
  - Mean ratios (`mirror / original`): `ratio_flesch_kincaid_grade=1.313`, `ratio_flesch_reading_ease=0.8659`.
  - Mean deltas (`mirror - original`): `delta_flesch_kincaid_grade=+1.927`, `delta_flesch_reading_ease=-11.53`.
  - This pattern is stable by party and condition: `ratio_flesch_kincaid_grade` ranges from `1.307` to `1.320`; `ratio_flesch_reading_ease` ranges from `0.8516` to `0.8921`.

- Keep/remove trend (answer to Q3): kept mirrors are more complex, and removed mirrors are easier to read.
  - All rows: keep vs remove `mirror_flesch_kincaid_grade` = `10.97` vs `10.22`; `mirror_flesch_reading_ease` = `48.76` vs `52.34`.
  - All rows: keep vs remove `ratio_flesch_kincaid_grade` = `1.317` vs `1.306`; `ratio_flesch_reading_ease` = `0.8753` vs `0.8467`.
  - The strongest behavioral split is in absolute mirror readability: kept mirrors have higher grade level and lower reading ease than removed mirrors.

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
