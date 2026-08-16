# Results, ambiguous cases

**Date:** 2026-08-16
**Status:** Complete
**Data:** Study Phase 2 Part 2 linked-fate trials only. No new language-model calls.

The design is in [`PROPOSAL.md`](./PROPOSAL.md). Run commands are in [`README.md`](./README.md).

## Analysis frame

| Quantity | Value |
|----------|------:|
| Linked-fate trials with usable post ids | 23,560 |
| Posts with three or more raters | 3,993 |
| Exact ties | 275 |

## E1. Noise floor and continuous scores

Fitted beta-binomial prior: alpha = 1.357, beta = 3.349. The prior mean remove probability is about 0.29.

| Check | Value |
|-------|------:|
| Half-split Pearson r on posts with six or more raters | 0.382 |
| Posts used in the half-split | 572 |
| Share of majority-keep@3 draws whose true p is below 0.25 | 0.599 |

The half-split correlation is modest, so three-rater labels are noisy. Under the fitted model, about 60% of majority-keep assignments at three raters come from posts whose true remove probability is still in the clear-keep region below 0.25. The old majority cells are heavily contaminated with clear cases that drew one noisy dissenting vote.

Artifacts: `outputs/e1/post_scores.csv`, `outputs/e1/summary.json`.

## E2. Rater severity versus post removability

| Quantity | Value |
|----------|------:|
| Variance share from rater effects | 0.763 |
| Variance share from post effects | 0.237 |
| Party-stance mismatch coefficient | -0.431 |
| Trials in the fit | 16,375 |
| Raters | 1,178 |

Most of the decision variance in the crossed logistic model sits in raters, not posts. A large share of observed disagreement is therefore rater severity rather than post-driven ambiguity. The party-stance mismatch coefficient is negative, so under linked fate a party mismatch does not raise removal odds in this fit.

Artifacts: `outputs/e2/post_effects.csv`, `outputs/e2/rater_effects.csv`, `outputs/e2/summary.json`.

## E3. Response time

Within-rater demeaned slopes of log response time on ambiguity:

| Predictor | Slope |
|-----------|------:|
| E1 ambiguity score | -0.060 |
| E2 adjusted ambiguity score | -0.154 |

Higher ambiguity scores are associated with faster decisions after length and trial-order controls, not slower ones. The quartile contrast points the same way: top-quartile E2 ambiguity mean log RT = 9.372, bottom quartile = 9.561, difference = -0.189. The timing pattern fits confident disagreement better than individual hesitation.

Artifacts: `outputs/e3/model_summary.json`, `outputs/e3/contrasts.csv`.

## E4. Stated rule groups

| Quantity | Value |
|----------|------:|
| Raters with a non-noise rule group | 215 |
| Raters unassigned | 963 |
| Observed cross-group share among disagreeing pairs | 0.586 |
| Null mean cross-group share | 0.627 |
| Share of null draws at least as large as observed | 0.935 |
| Disagreeing pairs used | 273 |

Most raters have no usable non-noise cluster assignment. Among the assigned subset, disagreeing pairs are not enriched for different rule groups relative to the permutation null. Rule-group conflict does not explain disagreement in this sparse mapping.

Artifacts: `outputs/e4/rater_rule_groups.csv`, `outputs/e4/group_severity.csv`, `outputs/e4/summary.json`.

## E5. Text predictability

| Metric | Value |
|--------|------:|
| Label test accuracy | 0.815 |
| Label test ROC AUC | 0.767 |
| Ambiguity test Pearson r | 0.458 |
| Ambiguity test R2 | 0.198 |
| One or two rater label-check accuracy | 0.780 |

Adjusted ambiguity is partly predictable from Titan embeddings plus deterministic surface features, but much more weakly than the keep/remove label. The grey-zone contrast using reused PRIME, intergroup, and valence labels shows enrichment in the top ambiguity quartile: grey-flag share 0.922 versus 0.624 in the bottom quartile.

Artifacts: `outputs/e5/metrics.json`, `outputs/e5/feature_importance.csv`, `outputs/e5/grey_zone_contrast.csv`.

## E6. Model difficulty and abstention

Qwen3 Next 80B error rates on posts with three or more raters:

| Band | n | Error rate |
|------|--:|----------:|
| Unanimous | 1,644 | 0.276 |
| Lopsided | 773 | 0.370 |
| Close | 1,576 | 0.402 |

Base accuracy on non-tie posts with three or more raters is 0.652. Abstaining on the top 30% by raw minority share raises accuracy to 0.688. The E1 and E2 ambiguity scores do not beat raw minority share at that abstention level.

Artifacts: `outputs/e6/error_by_band.csv`, `outputs/e6/abstention_curves.csv`, `outputs/e6/summary.json`.

## E7. Close-reading sample

Exported 120 unique posts for later reading:

| Stratum | n |
|---------|--:|
| Tie | 40 |
| High ambiguity with six or more raters | 40 |
| Unanimous at three raters with above-median E1 ambiguity | 40 |

No qualitative coding was run in this pass. The sample is for human review next.

Artifact: `outputs/e7/close_reading_sample.csv`.

## Reading across experiments

The clear-case versus grey-zone story is only partly supported.

Sampling noise is large. The beta-binomial fit says many majority labels at three raters are clear posts with one noisy dissent. Rater severity is also large. About three quarters of the crossed-model variance is in raters. Response times on high-ambiguity posts are faster, not slower, which does not support a story of shared individual hesitation.

A residual post-driven boundary still shows up in the data. Ambiguity has a text signal, grey-flag rhetoric is enriched at the top of the ambiguity distribution, and model errors concentrate where humans are closest. For practical abstention, the raw vote margin remains the best score among the three compared here.

## Limits

- Methods are descriptive. The writeups do not claim frequentist significance tests.
- E4 covers only 215 raters with non-noise clusters.
- E5 grey-zone flags reuse classifier labels from the earlier four-cell analysis and therefore omit most ties.
- E7 exports a sample and does not code it.
