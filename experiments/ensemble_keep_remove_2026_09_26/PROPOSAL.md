# Proposal: moderator archetypes and routed LLM juries for keep/remove prediction

Source: [issue 315](https://github.com/METResearchGroup/mirrorView-task/issues/315). Builds on [PR 309](https://github.com/METResearchGroup/mirrorView-task/pull/309) (Jev and GEPA), [PR 310](https://github.com/METResearchGroup/mirrorView-task/pull/310) (LoRA fine-tuning), [PR 313](https://github.com/METResearchGroup/mirrorView-task/pull/313) (Jev versus human vote counts), [PR 314](https://github.com/METResearchGroup/mirrorView-task/pull/314) (LoRA scores by vote count), and the issue 290 persona simulations in `experiments/ai_simulation_responses_2026_09_11/`.

All numbers in section 2 come from `preliminary_analysis.py` in this folder. The raw output is `outputs/preliminary_analysis.json`.

## 1. Summary

The issue proposes a two-path system. Jev decides whether a post is contested. If Jev is confident, the fine-tuned Qwen model labels the post. If Jev is not confident, a forum of five LLM agents, each given a moderator persona built from real participants, votes on the post, and we check whether the forum's split matches the human split.

The idea is sound in spirit, and the data supports its central premise, because human raters in our study differ from each other in stable, measurable ways that are not about party. Several parts of the plan need to change before it can produce a clean result, and the changes also give the paper a sharper claim.

- **Most posts are contested, so the router cannot separate "easy" from "hard" the way the issue describes.** 71.5% of five-rater posts have at least one dissenting vote. A post with a 20% remove probability still gets a split vote 67% of the time. Only about 3% of posts are extreme enough that a split is unlikely.
- **Most of the error on split posts is noise that no model can remove, if the model ignores who the raters are.** An oracle that knew every post's true population remove probability would still only match the observed five-rater majority 83.9% of the time. The LoRA adapters are already at about 79% to 81% on the same posts. Two independent panels of five humans would agree on the majority only 76.7% of the time.
- **A jury of personas that are drawn at random adds nothing beyond one number per post.** If raters are random draws from the population, the number of remove votes out of five follows a binomial distribution that depends only on the post's average remove probability. So a random-persona forum can only help by estimating that average better than a single model does. The forum does not add a richer kind of uncertainty.
- **The place where archetypes can beat everything else is prediction for known raters.** Rater leniency is stable (split-half reliability 0.80, against about 0.00 when we simulate raters with no individual differences). If we know which kinds of raters sit on a panel, we can in principle beat the 83.9% ceiling that applies to any predictor that ignores the raters.
- **Jev is a baseline and a routing signal, and it is not a target.** Raw Jev probabilities fit the human vote counts worse than a model that ignores the post entirely. After recalibration, Jev recovers about half of the explainable fit.

The proposed paper reframes the task from predicting the majority label to predicting the distribution of human judgments, shows that the remaining disagreement after the mirror procedure is structured and not partisan, recovers a small set of moderator archetypes from behavior, and tests whether LLM juries built from those archetypes reproduce both how much humans disagree and why.

## 2. What the existing data already shows

The analysis set is the combined Part 2 and Part 3 linked-fate export (`STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`). It has 101,020 scored decisions from 5,051 raters on 20,000 posts. Each rater saw a median of 20 posts, and 15,113 posts have exactly five raters.

### 2.1 How often humans disagree

| Remove votes out of 5 | Posts | Beta-binomial fit |
| ---: | ---: | ---: |
| 0 | 3,986 | 4,078.5 |
| 1 | 4,592 | 4,369.7 |
| 2 | 3,332 | 3,369.4 |
| 3 | 1,929 | 2,065.6 |
| 4 | 950 | 960.5 |
| 5 | 324 | 269.3 |

Only 28.5% of posts are unanimous. A beta-binomial model fits the counts closely. In the fitted model, each post has its own population remove probability $p$, drawn from Beta(1.73, 4.09), which has a mean of 0.30, and the five votes are independent draws with that probability.

The chance of a split vote at a given $p$ is $1 - p^5 - (1-p)^5$.

| True remove probability $p$ | Chance at least one of 5 raters dissents |
| ---: | ---: |
| 0.05 | 0.23 |
| 0.10 | 0.41 |
| 0.20 | 0.67 |
| 0.30 | 0.83 |
| 0.50 | 0.94 |

Under the fitted distribution, 65.5% of posts have $p$ between 0.2 and 0.8, so the band in the issue would send about two thirds of posts to the forum. Only 3.4% of posts have $p$ extreme enough that a unanimous vote is at least 80% likely.

### 2.2 Ceilings for any predictor that ignores who the raters are

The table below gives reference points for the case where a model knows everything about the post and nothing about the five raters.

| Quantity | Value |
| --- | ---: |
| Majority-label accuracy of an oracle that knows each post's $p$ | 0.839 |
| Chance two independent 5-rater panels give the same majority | 0.767 |
| Chance two independent 5-rater panels give the same remove count | 0.334 |
| Split-detection AUROC of an oracle that knows each post's $p$ | 0.794 |
| Count negative log-likelihood, oracle that knows each post's $p$ | 1.265 |
| Count negative log-likelihood, same prior for every post | 1.567 |

The oracle's accuracy by observed vote count is 0.99, 0.96, 0.86, 0.33, 0.58, and 0.80 for 0 through 5 remove votes. The value for 3 remove votes is low because most posts that happen to receive 3 of 5 removes have a true $p$ below 0.5, so the best rule calls them keep. PR 314's per-count accuracies should be read against these numbers. Weighted over five-rater posts, the PR 314 accuracies are about 0.79 for the modal adapter and 0.81 for the unanimous adapter. Those scores include training posts, so they are optimistic. Either way, there are at most a few points of majority accuracy left to gain for any model that ignores the raters.

The exact-count agreement of 0.334 means that a forum of five LLM votes cannot be judged by whether its count matches the five human votes. Two groups of real humans would match only a third of the time.

### 2.3 Jev as a predictor of the human vote distribution

| Jev A1 pair probabilities (n = 15,113) | Raw | Isotonic recalibration, 5-fold cross-fitted |
| --- | ---: | ---: |
| Count negative log-likelihood (lower is better) | 1.661 | 1.409 |
| Share of explainable fit recovered | below zero | 0.52 |
| Spearman correlation with remove votes | 0.524 | 0.521 |
| Split-detection AUROC | 0.619 | 0.694 |

"Share of explainable fit recovered" is (prior NLL minus model NLL) divided by (prior NLL minus oracle NLL). Raw Jev does worse than giving every post the same prior, because Jev predicts remove too often, as PR 313 found. Recalibration fixes much of the problem, and it should come before any use of Jev for routing. Jev's ranking of contested posts (AUROC 0.69) is meaningful, but it sits well below the oracle's 0.79.

### 2.4 Raters differ in stable ways, and the differences are not partisan

For each decision, we computed a residual, which is the rater's decision (1 for remove, 0 for keep) minus the remove rate of the other raters on the same post. A rater's mean residual measures how much more or less often the rater removes than other people who saw the same posts. Because the residual subtracts the post's consensus, it does not depend on which posts the rater happened to see.

| Test | Result |
| --- | ---: |
| Split-half reliability of rater mean residual | 0.80 |
| Same statistic when decisions are simulated with no rater differences | 0.00 |
| Rater remove rate, 10th, 25th, 50th, 75th, and 90th percentile | 0.00, 0.15, 0.30, 0.45, 0.60 |
| Raters who removed nothing | 11.0% |
| Democrat minus Republican mean residual | -0.015 (Cohen's d about 0.07, p = 0.015) |
| Failed attention check minus passed, mean residual | +0.061 (d about 0.27) |

Rater differences are large and stable, since a rater's leniency on one random half of their posts predicts their leniency on the other half. Party explains about 0.1% of the variance in rater leniency, which is consistent with the linked-fate design having removed most of the partisan pattern. Raters who failed the attention check remove more often than others, so part of what looks like disagreement is inattention.

Leniency is also not a single number. The correlation of a rater's residual on low-toxicity posts with their residual on high-toxicity posts is 0.27. After correcting for the reliability of each band's mean (0.47 and 0.60), the correlation is about 0.50. The corrected correlations for low versus middle and for middle versus high toxicity are about 0.91 and 0.84. Some raters remove mild posts that others keep, and a different set of raters are the ones who remove the harshest posts. One caution applies here. Residuals on a probability scale are bounded near 0 and 1, so a model with a single strictness threshold on the log-odds scale could also lower these correlations. Stage 0 below tests the number of dimensions on the log-odds scale, where this problem goes away.

### 2.5 What the earlier persona simulations found

In issue 290 (`experiments/ai_simulation_responses_2026_09_11/`), models were asked to simulate individual participants. Adding demographics (experiment 2) changed post-level remove F1 by less than 0.05 for most models. Adding the participant's own reflection text (experiment 3) helped more, e.g., GPT 5.4 nano went from 0.461 to 0.505 post-level F1. Individual simulation from a demographic profile is weak, and the richer signal is in what the rater said and did. The archetype plan should therefore build personas from behavior and rationale, not from demographics.

## 3. Corrections to the reasoning in the issue

The items below are the places where the plan in the issue would give a misleading answer, with the fix for each.

1. **The routing band does not match its stated meaning.** The issue describes 0.2 < p(remove) < 0.8 as "Jev thinks at least one of five would disagree." At $p = 0.2$, a split is already 67% likely, and at $p = 0.05$ it is still 23% likely. A band that captures "at least one dissent" would send nearly every post to the forum. The router should instead be chosen from a sweep of thresholds on a cost versus quality curve, using recalibrated probabilities (section 5.4).

2. **The high accuracy on unanimous posts is measured on posts selected by their outcome.** The fine-tuned model's roughly 95% accuracy is on posts that we already know were unanimous. In deployment the router selects posts by the model's own confidence, and some of those posts will be split. The confident path has to be scored on the posts the router actually sends to it.

3. **Weak performance on split posts is mostly not a model failure.** Section 2.2 shows that most of the error is the randomness of which five people were asked. A forum cannot fix that randomness for the majority label, so the forum's success cannot be measured by majority accuracy on split posts.

4. **Taking the forum's majority vote discards what the forum is for.** The quantity of interest is the forum's remove share (or better, the average of each agent's remove probability). Majority vote turns that share back into a single label.

5. **Five sampled personas are a noisy estimate of a quantity we can compute exactly.** If there are K archetypes with population weights $\pi_k$, and archetype $k$ removes the post with probability $p_k$, then a random rater removes with probability $\bar p = \sum_k \pi_k p_k$. We can compute $\bar p$ with K model calls per post. Sampling five random personas and counting their votes adds binomial noise on top of the estimate. Random sampling is useful only when we want to simulate one specific panel.

6. **Jev's uncertainty is not the target.** Jev is a miscalibrated estimator. Matching the forum to Jev would reward reproducing Jev's errors. The target is the human vote count, and Jev is a baseline and a candidate routing signal.

7. **Average embeddings of removed and kept posts would mostly measure which posts a rater was shown.** Each rater saw about 20 posts, of which about 6 were removed. The centroid of 6 embeddings is dominated by the topics of the assigned posts, and it says little about the rater's standards. The fix is to measure each rater against the consensus on the same posts, e.g., weight each post embedding by the rater's residual from section 2.4, or fit a model with a term for each post. The unadjusted centroid should stay in the study as a negative control.

8. **Twenty decisions per rater are too few to fit a separate rule set for each rater.** Individual profiles need to borrow strength across raters, e.g., by fitting a mixture of a few rater classes, where every rater in a class shares one set of weights. A mixture is also the natural way to get "archetypes" with population weights, which the issue asks for.

9. **Archetypes must be learned without the test posts.** If archetypes are fitted using raters' decisions on the posts we later evaluate, the forum's apparent match to human splits is partly leakage. Archetypes, rule cards, and exemplars must come only from training posts.

## 4. Research questions and hypotheses

- **RQ1. After the mirror procedure removes most partisan asymmetry, is the remaining disagreement noise or structure?**
  H1. A rater model with individual differences predicts held-out decisions better than a model with post effects only, and a model with two or more dimensions of rater difference beats a model with a single strictness dimension. Party and ideology explain little of the rater differences.
- **RQ2. Can a small set of moderator archetypes, recovered from behavior and labeled with stated rationales, describe the population of raters?**
  H2. A mixture with a small number of classes (we expect 3 to 6) is stable across resamples, gives better held-out fit than one class, and has classes that match recognizable moderation philosophies.
- **RQ3. Do LLM juries built from those archetypes predict the distribution of human judgments better than a single model?**
  H3a. On held-out five-rater posts, the archetype jury's $\bar p$ has lower count NLL than every single-model baseline, including a recalibrated model, a LoRA model trained on vote shares, and a single model sampled several times with no persona.
  H3b. Each LLM archetype agrees more with human raters of the same archetype than with human raters of other archetypes (discriminant validity). Without this test, a jury could get the right distribution for the wrong reasons.
- **RQ4. Can knowing the panel beat the ceiling for predictors that ignore the raters?**
  H4. Using each rater's archetype, inferred from their decisions on training posts, lowers the NLL of their decisions on test posts below what any rater-agnostic model can reach, including the oracle values in section 2.2.
- **RQ5. Does routing give most of the jury's benefit at a fraction of the cost?**
  H5. A router that sends only the posts most likely to be contested to the jury matches the jury's count NLL within a small margin while using a fraction of the model calls.

## 5. Experimental approach

### 5.1 Data, splits, and leakage rules

- **Posts.** Use the post-level 80/20 split from PR 310 (seed 1), so that no test post was seen by the LoRA adapters. Evaluate on test posts with exactly five raters (about 3,000 posts). Carve a development set out of the training posts for all tuning, including thresholds, K, and prompts.
- **Raters.** Archetype models are fit only on decisions on training posts. Every rater keeps their training decisions (about 16 per rater), which are used to infer their archetype for RQ4.
- **Cohort check.** Refit the main results with archetypes learned on Part 2 raters only and evaluated on Part 3 raters and posts, which come from a different catalog.
- **Rater quality.** Run every analysis both on all raters and after dropping raters who failed the attention check. Report both.
- **Primary target.** The number of remove votes out of five on test posts.

### 5.2 Stage 0. Measure the structure of disagreement (decides whether the rest is worth running)

Fit logistic models of each decision $y_{ij}$ for rater $i$ and post $j$, and compare them on held-out decisions (two held-out decisions per rater, from training posts only).

| Model | Form (log-odds of remove) | What it tests |
| --- | --- | --- |
| M0 | $\mu + v_j$ | Post effects only, no rater differences |
| M1 | $\mu + u_i + v_j$ | One strictness value per rater |
| M2 | $\mu + u_i + v_j + a_i^\top b_j$, with $a_i, b_j$ of size $d$ | $d$ dimensions of rater difference, for $d$ in 1, 2, 4, 8 |
| M3 | $\alpha_{c(i)} + \beta_{c(i)}^\top x_j + v_j$, with class $c(i)$ in 1 to K | K rater classes with weights on interpretable post features $x_j$ |

M2 is a logistic matrix factorization with rater and post embeddings. M3 is a latent class logistic regression, which is the source of the archetypes in Stage 1.

Outputs:

- Variance of rater effects compared with variance of post effects, on the log-odds scale.
- Held-out log-likelihood as a function of $d$ and K.
- Share of rater effect variance explained by party, ideology, the six policy attitudes, age, education, and attention check.

Decision rule:

- If M1 captures nearly all the gain of M2 and M3 over M0, disagreement is mostly one strictness dimension. The jury should then be a set of strictness levels, and rich personas are not needed. The paper is still viable, but its claim is about strictness.
- If M0 is close to M1, rater differences are too small to use, and the forum idea should stop. Section 2.4 suggests this outcome is unlikely.

### 5.3 Stage 1. Find moderator archetypes

**Post features.** Label every post with 10 to 20 interpretable binary features using an LLM. Start from existing feature work, i.e., `experiments/create_llm_features_2026_08_05/`, the feature clusters, the human criteria addendum, and the 87 GEPA criteria from PR 309. Candidates include insult aimed at a person, insult aimed at a group, profanity, threat or call for violence, dehumanizing language, unsupported factual claims, sarcasm, and whether the post makes an argument. Validate each feature on a hand-labeled sample of about 200 posts.

**Behavioral archetypes.** Fit M3 for K from 1 to 8. Choose K by held-out log-likelihood on development decisions, and check stability by refitting on bootstrap samples of raters and computing the adjusted Rand index between fits. Each class has a baseline strictness $\alpha_k$ and feature weights $\beta_k$, which say which features push that class toward remove. The class shares are the population weights $\pi_k$.

**Alternative archetype methods (ablations).**

- Cluster the rater embeddings $a_i$ from M2.
- Cluster residual-weighted post embeddings, i.e., for rater $i$, the sum over their posts of (decision minus leave-one-out consensus) times the post embedding. This is the issue's embedding idea, corrected for which posts the rater saw.
- Cluster the unadjusted centroid difference from the issue (negative control).
- Cluster only the stated rationales.
- Group by party and ideology.
- Group by strictness quantile only.

**Rationales.** Embed each rater's `phase1_pair_reflection_text` and have an LLM extract the rules the rater says they used. The reflection question asked mainly about how the pair view influenced them, so the text is a partial record of their standards. Test whether the rationale predicts the behavioral class (multinomial AUROC against a class-frequency baseline). A weak link here is itself a finding about the gap between stated and actual standards.

**Rule cards.** For each class, an LLM writes a rule card from three inputs, using training data only:

- The class's feature weights.
- A sample of rationales from raters in the class.
- Training posts where the class departed most from the consensus.

A person reviews each card for accuracy against the fitted weights.

**Who belongs to which archetype.** Fit a multinomial model of class on demographics and attitudes. The model gives the population weights for any target population (e.g., reweighting to a nationally representative sample), and it gives the partisanship result for RQ1.

### 5.4 Stage 2. Archetype juries

**Agent.** Qwen3.5 4B (the repo default), run on Hugging Face Jobs with vLLM. Each agent sees the study's linked-fate instructions, the pair view, and one archetype's rule card, with optional few-shot exemplars from that archetype's training decisions. Each agent returns keep or remove, and we read the probability of remove from the answer token log-probabilities.

**Aggregation.** The main estimate is $\bar p_j = \sum_k \pi_k \, p_{jk}$, the population remove probability, computed exactly from K calls. The predicted count distribution for a random five-rater panel is Binomial(5, $\bar p_j$). For RQ4, the prediction for a known panel is the product over its five raters of their class-weighted probabilities, using each rater's class posterior from training decisions.

**Baselines.** Every method below outputs a remove probability for each test post, and all are scored the same way.

| Baseline | Why it is included |
| --- | --- |
| Same prior for every post | Lower reference point |
| Jev A1, raw and isotonic-recalibrated | The current predictor and routing signal |
| Qwen LoRA modal adapter, remove probability from logits with temperature scaling | The current fine-tuned model |
| Qwen LoRA trained on vote shares (loss is binomial likelihood of the 5 votes) | The strongest direct estimator of $\bar p$, and the main competitor |
| Qwen zero-shot, N samples with no persona, remove share | Tests whether personas add anything beyond sampling noise |
| Qwen asked directly for "how many of 5 typical moderators would remove this" | Tests whether the model can state a distribution without personas |
| Demographic personas drawn from the rater pool (issue 290 style) | Tests archetypes against the persona method we already tried |
| Archetype-conditioned LoRA: one adapter trained on individual decisions with the rater's class as an input token | A trained version of the jury, following multi-annotator models |

### 5.5 Stage 3. Routing

A router scores each post, sends posts above a threshold $\tau$ to the jury, and sends the rest to the single fine-tuned model. Candidate routing scores are the probability of a split under recalibrated Jev, the same under the LoRA model, a cheap two-agent probe of the extreme archetypes, and a classifier trained to predict a split. The oracle router, which knows each post's true vote count, gives the upper bound.

For each score, sweep $\tau$ and plot model calls per post against count NLL and majority accuracy. The result is a cost versus quality curve, not a single threshold. The issue's 0.2 to 0.8 band on recalibrated probabilities is one point on the curve.

For deployment, the decision on a contested post is a policy choice, e.g., remove when $\bar p$ exceeds a threshold that the platform sets. The paper should present that threshold as a policy setting, and it should not tune the threshold to majority accuracy.

### 5.6 Metrics

**Primary metric.** Count NLL of the observed five votes under Binomial(5, predicted $p$), on test five-rater posts, also reported as the share of explainable fit recovered (section 2.3). The primary comparison is the archetype jury against the vote-share LoRA.

**Secondary metrics.**

- Brier score and a reliability diagram of predicted $p$ against observed remove share.
- Split-detection AUROC, compared with the oracle's 0.794.
- Majority accuracy and remove F1, compared with the 0.839 ceiling.
- Discriminant validity (H3b). A K by K matrix of agreement between LLM archetype k and held-out decisions of human raters in class k'. We want the diagonal to beat the rest of its row.
- Individual decision NLL and AUROC for RQ4, as a function of how many training decisions per rater are used (0, 5, 10, all).
- Model calls per post.
- Diversity of the jury, e.g., the spread of $p_{jk}$ across archetypes on each post, compared with the spread of the human class probabilities on the same post.

**Statistics.** Paired bootstrap over posts (1,000 resamples) for post metrics, and a bootstrap that resamples whole raters for individual metrics. Fix the primary metric, the primary comparison, and the test split before running Stage 2, and apply Holm correction within the family of hypotheses H3a, H3b, H4, and H5.

## 6. Ablations

Priority P0 is needed for the paper's main claims, P1 strengthens them, and P2 is optional.

| Group | Ablation | Values | Priority |
| --- | --- | --- | --- |
| Structure | Dimensions of rater difference (M2) | $d$ = 0, 1, 2, 4, 8 | P0 |
| Structure | Attention-check filter | all raters, passed only | P0 |
| Archetypes | Number of classes (M3) | K = 1, 2, 3, 4, 6, 8 | P0 |
| Archetypes | Method | latent class on features, M2 embedding clusters, residual-weighted embeddings, unadjusted centroids, rationale only, party and ideology, strictness quantiles | P0 for latent class, strictness quantiles, and unadjusted centroids, P1 for the rest |
| Persona content | What the agent sees | rule card only, rule card plus 4 or 8 exemplars, demographic sketch, one real rater's rationale, no persona | P0 |
| Aggregation | How votes become $p$ | exact weighted mixture of soft probabilities, 5 sampled personas with hard votes (the issue's design), 15 or 25 sampled personas, majority vote only | P0 |
| Aggregation | Class weights | fitted $\pi_k$, equal weights | P1 |
| Interaction | Agents see each other | independent, one round where agents read the others' reasons and may revise | P1 |
| Model | Agent model | Qwen3.5 4B zero-shot, archetype-conditioned LoRA, a larger API model | P0 for the first two, P1 for the API model |
| Model | Sampling temperature | 0, 0.7, 1.0 | P2 |
| Routing | Routing score | recalibrated Jev, LoRA, two-agent probe, split classifier, oracle | P0 |
| Routing | Threshold | full sweep | P0 |
| Individual | Rater calibration decisions | 0, 5, 10, all training decisions | P0 |
| Input | Text shown | pair, original only | P2 |
| Cohort | Train and test cohorts | random split, Part 2 to Part 3 | P1 |

The deliberation ablation is included because discussion between agents tends to push them toward agreement, which would shrink the jury's spread. If deliberation lowers diversity and hurts NLL, that is a useful negative result for multi-agent designs.

## 7. Core narrative for the paper

### 7.1 Working titles

- "What disagreement remains after the mirror? Moderator archetypes and LLM juries for symmetric content moderation"
- "Predicting how people disagree about content moderation, not just what the majority decides"

### 7.2 The argument, in the order a paper would make it

1. **Setting.** Content moderation of political speech is contested, and much of the contest is partisan. The MirrorView linked-fate procedure asks raters to keep or remove a post together with its mirrored opposite, so a rater cannot treat the two sides differently.
2. **Finding 1. The mirror removes the partisan pattern, but it does not remove disagreement.** In over 100,000 decisions, party explains about 0.1% of the variance in rater strictness, yet 71.5% of posts get a split vote.
3. **Finding 2. The remaining disagreement has structure.** Raters differ in stable ways (reliability 0.80), and the differences have more than one dimension. The mild-post removers are partly different people from the harsh-post removers. A few archetypes describe most of the variation, and we name them from what raters did and what they said.
4. **Finding 3. Majority accuracy is the wrong measure for contested content.** For any model that ignores who the raters are, the best possible majority accuracy is 0.839, and two human panels agree only 76.7% of the time. Current fine-tuned models are already close to that limit. The task that remains open is to predict the distribution of judgments, which recent work calls distributional pluralism.
5. **Method. Archetype juries.** We turn each archetype into an LLM agent with a rule card, and we combine the agents with the archetypes' population shares. We compare the jury with strong single-model estimators, including one trained directly on vote shares.
6. **Finding 4. Whether the jury recovers human disagreement, and whether it does so for the right reasons.** We report fit to vote counts, calibration, which posts are contested, and the discriminant validity test.
7. **Finding 5. Knowing the panel beats the ceiling.** With a rater's archetype inferred from a few earlier decisions, predictions for that rater beat every rater-agnostic model. This result has a practical use, e.g., choosing or weighting moderators on purpose.
8. **Finding 6. Routing makes the jury affordable.** Most of the benefit comes from sending the most contested posts to the jury.
9. **Implications.** A platform can report how contested a decision is, choose whose standards count by setting the archetype weights, and stop treating disagreement as label noise. We also discuss the risks, including stereotyped personas and the fact that the archetypes come from one crowdworker population.

### 7.3 Contributions

- A measurement of how much disagreement is left, and how much of it is structured, after a procedure that forces raters to treat both political sides the same.
- Ceilings for majority and distribution prediction on multi-rater moderation data, and a demonstration that current models are near the majority ceiling.
- A method to recover moderator archetypes from sparse behavioral data (about 20 decisions per rater) that adjusts for which posts each rater saw, and that links the archetypes to stated rationales.
- An evaluation of LLM juries against strong single-model baselines, with a discriminant validity test for personas.
- A routed system that shows the trade-off between cost and quality.

### 7.4 Planned figures

1. The system diagram, from post to router, then to the single model or the archetype jury, and finally to the predicted vote distribution.
2. The human vote histogram with the beta-binomial fit, rater strictness reliability, and the party comparison.
3. Majority accuracy by vote count for Jev and the LoRA models, drawn against the oracle ceiling (the figure that reframes the task).
4. The archetype map, a heatmap of class feature weights with a short summary of each rule card and each class's share.
5. Reliability diagrams and the share of explainable fit recovered for every method.
6. The discriminant validity matrix.
7. Cost versus quality curves for each routing score.
8. The learning curve for individual predictions as the number of known decisions per rater grows, drawn against the rater-agnostic ceiling.

### 7.5 Related work to position against

These references should be checked before citing, since the list was written from memory.

- Learning from annotator disagreement. Plank (2022), "The 'problem' of human label variation", and Uma et al. (2021), "Learning from disagreement: a survey".
- Multi-annotator and jury models. Davani, Díaz, and Prabhakaran (2022), "Dealing with disagreements", and Gordon et al. (2022), "Jury learning". Jury learning is the closest prior work, and our difference is that the jurors are LLM agents built from archetypes found in behavior.
- Annotator identity and toxicity. Sap et al. (2022), "Annotators with attitudes", and Kumar et al. (2021), "Designing toxic content classification for a diversity of perspectives".
- Latent rater classes. Dawid and Skene (1979).
- Pluralistic and distributional alignment. Sorensen et al. (2024), "A roadmap to pluralistic alignment", and Meister, Guestrin, and Hashimoto (2024), "Benchmarking distributional alignment of large language models".
- LLM simulation of people. Argyle et al. (2023), "Out of one, many", Santurkar et al. (2023), "Whose opinions do language models reflect?", Hu and Collier (2024), "Quantifying the persona effect in LLM simulations", and Wang, Morgenstern, and Dickerson (2025) on LLMs flattening identity groups.
- Deferral and cascades. Madras, Pitassi, and Zemel (2018), "Predict responsibly", Mozannar and Sontag (2020), and Chen, Zaharia, and Zou (2023), "FrugalGPT".

## 8. Threats to validity

- **Persona collapse and stereotyping.** LLM personas often have less spread than the people they simulate, and they can exaggerate group traits. The diversity metric and the discriminant validity test are there to detect both problems.
- **Small model.** Qwen3.5 4B may not follow nuanced rule cards. The archetype-conditioned LoRA and the larger API model ablation address this risk.
- **Feature quality.** If the LLM post features are noisy, the classes in M3 will be blurred. Each feature needs validation on hand labels, and M2, which needs no features, serves as a check.
- **Stated versus actual standards.** The reflection text answers a narrower question than "what are your rules", so rationale-based personas may underperform, which is a finding in itself.
- **Inattentive raters.** Some apparent disagreement is inattention. The attention-check filter separates the two, and a latent class for inattentive raters may appear in M3 on its own.
- **Scope of the ceiling.** The 0.839 and 1.265 values apply only to predictors that ignore the raters, and they assume the beta-binomial model, which fits well but slightly underpredicts unanimous remove posts (324 observed against 269 expected).
- **Generality.** All raters did linked-fate moderation of political posts on Prolific. The archetypes may not carry over to moderation of single posts, other topics, or professional moderators.
- **Many comparisons.** The ablation grid is large, so the primary metric and comparison are fixed in advance, and everything else is reported as exploratory.

## 9. Compute and cost

The costs below are counts of work, not time.

- **Stage 0 and Stage 1.** CPU only for the rater models. The post feature labeling is one LLM call per post and feature group over 20,000 posts, which fits the existing Bedrock or OpenAI batch runners.
- **Stage 2.** K calls per test post for the exact jury, i.e., about 3,000 posts times K up to 8, so under 25,000 calls per configuration. The sampled-persona ablations with 25 agents are about 75,000 calls. All of these runs are small for vLLM on one Hugging Face Jobs GPU.
- **Vote-share LoRA and archetype-conditioned LoRA.** Two more training runs on the PR 310 setup.
- **Storage.** All predictions and fitted models go to `s3://mirrorview-experimental-artifacts/experiments/ensemble_keep_remove_2026_09_26/`.

## 10. Suggested order of work

1. Stage 0 on training posts, with the decision rule in section 5.2.
2. The single-model baselines on the test posts, including the vote-share LoRA. These baselines are useful even if the jury fails.
3. Stage 1 archetypes and rule cards, with human review of the cards.
4. Stage 2 juries (P0 ablations), then the discriminant validity test.
5. RQ4 individual prediction.
6. Stage 3 routing curves.
7. P1 ablations and the Part 2 to Part 3 cohort check.

## 11. Open decisions for the team

- **Primary claim.** The paper can be framed around distribution prediction (RQ3) or around prediction for known raters (RQ4). RQ4 is the more novel claim, and RQ3 is the safer one.
- **Decision policy for contested posts.** The team needs to pick the remove threshold on $\bar p$, or decide to report it as a setting.
- **New data collection.** A small follow-up study could test RQ4 prospectively, by giving new raters about 10 diagnostic posts chosen to identify their archetype and then predicting their decisions on new posts. The follow-up is optional, but it would be the strongest evidence for RQ4.
