# Results, unanimous vs majority labels

**Date:** 2026-08-09  
**Status:** Complete  
**Method:** Descriptive only (no hypothesis tests, no confidence intervals)

The design contract is in [`GRILL.md`](./GRILL.md). The run commands are in [`README.md`](./README.md).

## Cohort

The cohort file is `outputs/cohort/four_cell_cohort.csv`.

The analysis set is linked-fate posts with at least three raters. Exact ties are dropped. The total count is **n = 3,718**.

| Cell | n |
| ---- | -: |
| `unanimous_keep` | 1,490 |
| `majority_keep` | 1,480 |
| `majority_remove` | 594 |
| `unanimous_remove` | 154 |

## Analysis 1, surface metrics and classifiers on original text

The cell summary file is `outputs/analysis1/cell_summary.csv`.

Continuous columns are cell medians. Classifier columns are cell shares.

| Cell | n | High toxicity share | Median chars | Median words | Median sentences | Median avg sentence length | Median punctuation density | Median FK grade | Median reading ease | Share positive | Share intergroup | Share PRIME (`is_prime`) |
| ---- | -: | ------------------: | -----------: | -----------: | ---------------: | -------------------------: | -------------------------: | --------------: | ------------------: | -------------: | ---------------: | -----------------------: |
| `unanimous_keep` | 1,490 | 4.6% | 203.0 | 34.0 | 2.0 | 13.67 | 0.028 | 8.77 | 57.83 | 0.292 | 0.681 | 0.749 |
| `majority_keep` | 1,480 | 19.2% | 183.5 | 32.0 | 2.0 | 13.00 | 0.029 | 7.89 | 62.75 | 0.161 | 0.764 | 0.836 |
| `majority_remove` | 594 | 52.5% | 146.0 | 26.0 | 2.0 | 12.00 | 0.030 | 7.05 | 66.83 | 0.040 | 0.842 | 0.958 |
| `unanimous_remove` | 154 | 70.8% | 131.5 | 24.0 | 2.0 | 10.38 | 0.032 | 6.68 | 66.37 | 0.032 | 0.851 | 0.948 |

The rows for each post are in `outputs/analysis1/per_post_features.csv`.

## Analysis 2, Stage 1 features and word clouds

Coverage counts come from `outputs/analysis2/coverage.json`.

| Quantity | Value |
| -------- | ----: |
| Cohort posts | 3,718 |
| Reused prior Stage 1 posts | 232 |
| Newly generated posts | 3,486 |
| Missing after run | 0 |
| Merged feature rows | 12,911 |

The merged features file is `outputs/analysis2/merged_stage1_features.jsonl`.

Word size in each cloud follows how many posts in the cell contain the token. The cloud images are:

- `outputs/analysis2/wordcloud_unanimous_keep.png`
- `outputs/analysis2/wordcloud_majority_keep.png`
- `outputs/analysis2/wordcloud_majority_remove.png`
- `outputs/analysis2/wordcloud_unanimous_remove.png`

The full top token table is `outputs/analysis2/top_tokens_by_cell.csv`. The top 10 tokens for each cell are shown below.

### Unanimous keep

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | policy | 266 |
| 2 | blame | 204 |
| 3 | medium | 197 |
| 4 | multiple | 188 |
| 5 | explicit | 179 |
| 6 | political | 161 |
| 7 | gun | 150 |
| 8 | climate | 144 |
| 9 | claim | 143 |
| 10 | moral | 143 |

### Majority keep

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | blame | 248 |
| 2 | multiple | 205 |
| 3 | policy | 202 |
| 4 | political | 189 |
| 5 | explicit | 183 |
| 6 | medium | 162 |
| 7 | direct | 161 |
| 8 | gun | 156 |
| 9 | moral | 146 |
| 10 | strong | 141 |

### Majority remove

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | political | 120 |
| 2 | profanity | 110 |
| 3 | blame | 103 |
| 4 | direct | 80 |
| 5 | group | 76 |
| 6 | strong | 75 |
| 7 | explicit | 75 |
| 8 | insult | 71 |
| 9 | multiple | 69 |
| 10 | moral | 62 |

### Unanimous remove

| Rank | Token | n posts |
| ---: | ----- | ------: |
| 1 | profanity | 54 |
| 2 | political | 41 |
| 3 | explicit | 29 |
| 4 | strong | 28 |
| 5 | insult | 27 |
| 6 | blame | 26 |
| 7 | group | 25 |
| 8 | direct | 24 |
| 9 | insults | 22 |
| 10 | multiple | 21 |

## Analysis 3, stance by cell within toxicity strata

The long table is `outputs/analysis3/stance_by_cell_all_strata.csv`, and the three wide tables for each toxicity stratum sit beside it. Cell counts sum to 3,718 across the three strata.

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

The primary claim is supported in a descriptive sense by a clear order across the four cells. High toxicity share rises from unanimous keep (4.6%) through majority keep (19.2%) and majority remove (52.5%) to unanimous remove (70.8%). Median original text length falls in the same order, from 203 characters to 183.5, then 146, then 131.5. The share of positive valence falls toward the remove cells, while the intergroup and PRIME shares rise. Unanimous cells sit at the ends of those patterns, and majority cells sit between them.

The secondary claim is also supported in a descriptive sense. Remove cells are not a clean left versus right story. In the high toxicity stratum, both left and right posts appear in majority remove and unanimous remove in large numbers, so stance alone does not separate keep from remove the way high toxicity does. The Stage 1 token tables point in the same direction, because tokens such as `profanity` and `insult` rise toward unanimous remove, while keep cells stay closer to framing and policy language.

The readings above are descriptive. They do not claim statistical significance.

## Limitations

- Valence, intergroup, and PRIME classifier labels can change across model calls.
- Stage 1 features used the dual text prompt with original and mirror text, so that new rows stay comparable to reused rows from `create_llm_features`.
- PRIME is reported as one binary `is_prime` label, not as four separate prestige, in group, moral, and emotional cue columns.
- Exact ties were excluded, and they are not described here.
