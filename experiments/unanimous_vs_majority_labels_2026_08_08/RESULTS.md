# RESULTS — Unanimous vs majority labels

**Date:** 2026-08-09  
**Status:** Complete  
**Method:** Descriptive only (no hypothesis tests, no confidence intervals)

Contract: [`GRILL.md`](./GRILL.md). Runbook: [`README.md`](./README.md).

## Cohort

Source: `outputs/cohort/four_cell_cohort.csv`

Linked-fate posts with at least three raters. Exact ties dropped. Total **n = 3,718**.

| Cell | n |
| ---- | -: |
| `unanimous_keep` | 1,490 |
| `majority_keep` | 1,480 |
| `majority_remove` | 594 |
| `unanimous_remove` | 154 |

## Analysis 1 — Surface metrics and classifiers (original text)

Source: `outputs/analysis1/cell_summary.csv`

Continuous columns are cell medians. Classifier columns are cell shares.

| Cell | n | High toxicity share | Median chars | Median words | Median sentences | Median avg sentence length | Median punctuation density | Median FK grade | Median reading ease | Share positive | Share intergroup | Share PRIME (`is_prime`) |
| ---- | -: | ------------------: | -----------: | -----------: | ---------------: | -------------------------: | -------------------------: | --------------: | ------------------: | -------------: | ---------------: | -----------------------: |
| `unanimous_keep` | 1,490 | 4.6% | 203.0 | 34.0 | 2.0 | 13.67 | 0.028 | 8.77 | 57.83 | 0.292 | 0.681 | 0.749 |
| `majority_keep` | 1,480 | 19.2% | 183.5 | 32.0 | 2.0 | 13.00 | 0.029 | 7.89 | 62.75 | 0.161 | 0.764 | 0.836 |
| `majority_remove` | 594 | 52.5% | 146.0 | 26.0 | 2.0 | 12.00 | 0.030 | 7.05 | 66.83 | 0.040 | 0.842 | 0.958 |
| `unanimous_remove` | 154 | 70.8% | 131.5 | 24.0 | 2.0 | 10.38 | 0.032 | 6.68 | 66.37 | 0.032 | 0.851 | 0.948 |

Per-post rows: `outputs/analysis1/per_post_features.csv`

## Analysis 2 — Stage 1 features and word clouds

Coverage (`outputs/analysis2/coverage.json`):

| Quantity | Value |
| -------- | ----: |
| Cohort posts | 3,718 |
| Reused prior Stage 1 posts | 232 |
| Newly generated posts | 3,486 |
| Missing after run | 0 |
| Merged feature rows | 12,911 |

Merged features: `outputs/analysis2/merged_stage1_features.jsonl`

Word clouds (token size follows post document frequency):

- `outputs/analysis2/wordcloud_unanimous_keep.png`
- `outputs/analysis2/wordcloud_majority_keep.png`
- `outputs/analysis2/wordcloud_majority_remove.png`
- `outputs/analysis2/wordcloud_unanimous_remove.png`

Top tokens by cell (`outputs/analysis2/top_tokens_by_cell.csv`; top 10 shown):

### Unanimous keep

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | vs | 351 |
| 2 | framing | 334 |
| 3 | short | 318 |
| 4 | policy | 266 |
| 5 | uses | 246 |
| 6 | blame | 204 |
| 7 | medium | 197 |
| 8 | multiple | 188 |
| 9 | explicit | 179 |
| 10 | via | 179 |

### Majority keep

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | vs | 328 |
| 2 | uses | 318 |
| 3 | short | 308 |
| 4 | framing | 283 |
| 5 | blame | 248 |
| 6 | multiple | 205 |
| 7 | policy | 202 |
| 8 | via | 189 |
| 9 | political | 189 |
| 10 | explicit | 183 |

### Majority remove

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | uses | 165 |
| 2 | political | 120 |
| 3 | profanity | 110 |
| 4 | blame | 103 |
| 5 | framing | 100 |
| 6 | short | 99 |
| 7 | direct | 80 |
| 8 | vs | 79 |
| 9 | group | 76 |
| 10 | strong | 75 |

### Unanimous remove

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | profanity | 54 |
| 2 | uses | 54 |
| 3 | political | 41 |
| 4 | explicit | 29 |
| 5 | strong | 28 |
| 6 | short | 28 |
| 7 | insult | 27 |
| 8 | blame | 26 |
| 9 | group | 25 |
| 10 | framing | 24 |

## Analysis 3 — Stance by cell within toxicity strata

Source: `outputs/analysis3/stance_by_cell_all_strata.csv` (and the three stratum-specific wide CSVs). Cell counts sum to 3,718 across strata.

### Low toxicity (n = 1,043)

| Stance | unanimous_keep | majority_keep | majority_remove | unanimous_remove |
| ------ | -------------: | ------------: | --------------: | ---------------: |
| left | 396 | 205 | 20 | 2 |
| right | 262 | 142 | 15 | 1 |

### Middle toxicity (n = 1,902)

| Stance | unanimous_keep | majority_keep | majority_remove | unanimous_remove |
| ------ | -------------: | ------------: | --------------: | ---------------: |
| left | 344 | 383 | 110 | 18 |
| right | 420 | 466 | 137 | 24 |

### High toxicity (n = 773)

| Stance | unanimous_keep | majority_keep | majority_remove | unanimous_remove |
| ------ | -------------: | ------------: | --------------: | ---------------: |
| left | 40 | 108 | 115 | 76 |
| right | 28 | 176 | 197 | 33 |

## Descriptive reading

Primary claim: The four cells line up as a gradient. High-toxicity share rises from unanimous keep (4.6%) through majority keep (19.2%) and majority remove (52.5%) to unanimous remove (70.8%). Median original-text length falls along the same order (203 → 183.5 → 146 → 131.5 characters). Positive valence falls and intergroup and PRIME shares rise toward the remove cells. Unanimous cells sit at the ends; majority cells sit in between.

Secondary claim: Remove cells are not a clean left-versus-right story. In high toxicity, both left and right posts appear in majority remove and unanimous remove in large numbers. Stance alone does not separate keep from remove the way high toxicity does. Stage 1 token tables reinforce a threshold-violation flavor in remove cells: `profanity` and `insult` rise toward unanimous remove, while keep cells stay closer to framing and policy language.

These readings are descriptive. They do not claim statistical significance.

## Limitations

- Valence, intergroup, and PRIME classifier labels can change across model calls.
- Stage 1 features used the dual-text prompt (original + mirror) for parity with reused rows from `create_llm_features`.
- PRIME is reported as one binary `is_prime` label, not four separate prestige / in-group / moral / emotional cue columns.
- Exact ties were excluded and are not characterized here.
