# Results

Stage A and Stage B tables will be written here.

## Stage A: Jev baselines (cohort A, n=14,955)

Headline metrics: **test split only**, threshold **0.5**, positive class **remove**.

| Ablation | View | Accuracy | Precision | Recall | F1 | Balanced acc | ROC-AUC | PR-AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1_pair_study_prompt | pair | 0.7309 | 0.4211 | 0.7033 | 0.5267 | 0.7208 | 0.7936 | 0.5342 |
| A2_original_only | original | 0.7419 | 0.4252 | 0.6028 | 0.4987 | 0.6912 | 0.7722 | 0.4919 |
| A3_mirror_only | mirror | 0.7760 | 0.4783 | 0.5699 | 0.5201 | 0.7008 | 0.7725 | 0.5291 |
| A4_pair_features_addendum | pair + addendum | 0.5249 | 0.2994 | 0.9184 | 0.4516 | 0.6684 | 0.8118 | 0.5579 |

Test split trivial baselines (A1): keep-all F1 **0.0000**, remove-all F1 **0.3512**, prevalence-random F1 **0.2116** (std **0.0143**).

Dev-tuned threshold (fit on dev, applied to test):

| Ablation | Dev threshold | Test F1 |
| --- | --- | --- |
| A1_pair_study_prompt | 0.4500 | 0.5123 |
| A2_original_only | 0.4500 | 0.5000 |
| A3_mirror_only | 0.5000 | 0.5201 |
| A4_pair_features_addendum | 0.8000 | 0.5664 |

Spearman(P(remove), remove_share) on full cohort:

| Ablation | rho |
| --- | --- |
| A1_pair_study_prompt | 0.4927 |
| A2_original_only | 0.4638 |
| A3_mirror_only | 0.4544 |
| A4_pair_features_addendum | 0.5230 |

Latency at batch size 10 (A1, full cohort):

| Level | p50 ms | p90 ms | p99 ms |
| --- | --- | --- | --- |
| per request | 369.8 | 687.5 | 1547.4 |
| per post | 37.0 | 68.7 | 154.7 |

Stage A Jev cost (from results.json): **$1.45** total (estimates.md expected ~$0.93).

## Stage B: Jev + GEPA (test split, threshold 0.5, positive class remove)

| Ablation | View | Dev F1 (selected) | Test F1 | Test ROC-AUC | Reflection LM | Reflection cost USD |
| --- | --- | --- | --- | --- | --- | --- |
| B1_gepa_pair | pair | 0.5534 | 0.5484 | 0.8132 | openai/gpt-6-luna | 0.00 |
| B1T_gepa_pair_terra | pair | 0.5592 | 0.5635 | 0.8132 | openai/gpt-5.6-terra | 0.00 |
| B2_gepa_original | original | 0.5491 | 0.5372 | 0.8047 | openai/gpt-6-luna | 0.00 |
| B3_gepa_mirror | mirror | 0.5535 | 0.5536 | 0.8068 | openai/gpt-6-luna | 0.00 |
| B4_gepa_asymmetric_reward | pair (asymmetric train) | 0.5464 | 0.5295 | 0.8066 | openai/gpt-6-luna | 0.00 |

Stop reason for all five optimizations: **max_metric_calls** (~9058–9062 calls; budget 9000). Reflection cost was not written to Wandb summary (`dev_selection.json` shows $0.00).

### B1 vs B1-T (stronger reflection ablation)

| Metric | B1_gepa_pair | B1T_gepa_pair_terra | Delta (Terra − Luna) |
| --- | --- | --- | --- |
| Dev F1 | 0.5534 | 0.5592 | +0.0058 |
| Test F1 | 0.5484 | 0.5635 | +0.0151 |
| Reflection cost USD | 0.00 | 0.00 | 0.00 |

B1-T improves both dev and test F1 vs B1 under the same pair-view training setup.

### Transfer evals (test split F1)

| Transfer | Prompt source | Scoring view | Test F1 |
| --- | --- | --- | --- |
| B1 on original | B1_gepa_pair | original | 0.3131 |
| B1 on mirror | B1_gepa_pair | mirror | 0.2000 |
| B2 on mirror | B2_gepa_original | mirror | 0.5444 |
| B3 on original | B3_gepa_mirror | original | 0.5523 |

## Spend vs estimates.md

| Item | Actual USD | estimates.md |
| --- | --- | --- |
| Stage A Jev | 1.45 | ~0.93 |
| Stage B Jev (5 GEPA runs, estimated) | ~4.35 | ~4.35 |
| Stage B Jev (test + transfer evals, measured) | 1.60 | <0.10 transfer only |
| Luna reflection (4 runs) | 0.00 (not logged) | ~1.80 to ~3.00 (cap 20 total) |
| Terra reflection (B1-T) | 0.00 (not logged) | ~10 to ~17 (cap 20) |
| **Project total (measured Jev + logged reflection)** | **~7.40** | **~17 to ~26 (hard ceiling ~46)** |

Measured Jev: Stage A $1.45 + GEPA-phase estimate $4.35 (from metric-call volume) + test eval $0.77 + transfer eval $0.83 = **~$7.40**. OpenAI reflection spend was not captured in run artifacts; actual total is likely higher than $7.40 but below the ~$46 hard cap.
