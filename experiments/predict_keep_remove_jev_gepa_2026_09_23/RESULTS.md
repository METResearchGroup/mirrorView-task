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
