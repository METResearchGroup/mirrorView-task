# Unanimous vs majority labels (2026-08-08)

Linked-fate Study Phase 2 Part 2 posts can receive the same keep or remove label whether every rater agrees or only a strict majority agrees. This experiment asks whether those cases differ in measurable ways.

The grill lock is in [`GRILL.md`](./GRILL.md). Descriptive findings live in [`RESULTS.md`](./RESULTS.md).

## Claims

Primary: Unanimous keep and unanimous remove sit at clearer extremes of content. Strict-majority keep and remove sit more in the middle on toxicity and length and look more arguable.

Secondary: Heavy remove looks more like high toxicity than like a left versus right political split. That claim is descriptive only, tested with toxicity strata and stance tables.

Method: Descriptive only. No hypothesis tests and no confidence intervals.

## Cohort

Universe: linked-fate trials with at least three raters.

Four cells:

| Cell | Expected n (current data) |
| ---- | ------------------------: |
| `unanimous_keep` | 1,490 |
| `majority_keep` | 1,480 |
| `majority_remove` | 594 |
| `unanimous_remove` | 154 |

Exact ties are dropped and are not analyzed. The cohort file is experiment-local. It is not a new shared registry dataset.

Path: `outputs/cohort/four_cell_cohort.csv`

## Text and joins

Analyses 1 and 3 (and length or toxicity summaries) use `original_text` only.

Toxicity strata come from `sample_toxicity_type` in `{low, middle, high}`.

Stance comes from stimuli `sampled_stance` in `{left, right}`.

## Analysis 1

Surface metrics and classifiers on original text, summarized by cell:

- Length and structure: character, word, and sentence counts; average sentence length; punctuation density
- Readability: Flesch–Kincaid grade; reading ease
- Classifiers from `shared/textual_features/`: valence (`is_positive`), intergroup (`is_intergroup`), and PRIME as the shared binary `is_prime` label (not four separate cue columns)

Outputs: `outputs/analysis1/per_post_features.csv`, `outputs/analysis1/cell_summary.csv`

## Analysis 2

Stage 1 LLM features only (no embed, cluster, or label stages).

Cover every four-cell post. Reuse Stage 1 rows from `experiments/create_llm_features_2026_08_05/` when `message_id` overlaps. Generate only missing ids with the dual-text prompt (original + mirror) so new rows stay comparable to reused rows. Do not write into that experiment’s outputs tree.

Token counting for word clouds:

1. Split `feature_value` on non-letter characters and lowercase
2. Drop stopwords, single-character tokens, low-content tokens, and meta tokens (`mirror`, `original`, …)
3. Count each remaining token at most once per post inside each cell
4. Take the top 30 tokens by that post count

Outputs:

- `outputs/analysis2/coverage.json`
- `outputs/analysis2/merged_stage1_features.jsonl`
- `outputs/analysis2/top_tokens_by_cell.csv`
- `outputs/analysis2/wordcloud_<cell>.png` for each of the four cells

## Analysis 3

Three stance-by-cell tables, one per toxicity stratum: `sampled_stance` (left or right) × the four cells.

Outputs: `outputs/analysis3/stance_by_cell_{low,middle,high}_toxicity.csv` and `outputs/analysis3/stance_by_cell_all_strata.csv`

## How to run

From the repo root:

```bash
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py
PYTHONPATH=. uv run --with wordcloud python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py
```

Analysis 2 feature generation needs an OpenAI API key in the environment (same path as other LLM experiment scripts).

## Out of scope

- Analyzing exact ties
- Formal statistical tests or confidence intervals
- Work under `experiments/rater_agreement_2026_08_06/`
- Stages 2 through 4 of `experiments/create_llm_features_2026_08_05/` (embed, cluster, label)
- New shared transformed catalog entries
- A strategy document writeup
