# Proposal, separating ambiguous boundary cases from clear cases

**Date:** 2026-08-16
**Status:** Proposal only, no experiments run yet
**Data:** Study Phase 2 Part 2 linked-fate trials and existing derived artifacts only. No new data collection.

## 1. Why this work

The methods writeup ([`docs/study_updates/METHODS_WRITEUP_2026_08_13.md`](../../docs/study_updates/METHODS_WRITEUP_2026_08_13.md)) says there is a chunk of posts the model has trouble predicting, and it guesses that people are not fully sure about those posts either. The four-cell analysis ([`unanimous_vs_majority_labels_2026_08_08`](../unanimous_vs_majority_labels_2026_08_08/)) was one step toward testing that guess. It showed that unanimous keep and unanimous remove posts sit at the extremes of toxicity, length, and valence, while posts with a split vote sit in the middle.

What we do not yet have is a defensible way to say, for a given post, "this post is genuinely ambiguous" as opposed to "this post looks ambiguous because of how we sampled raters." The current unanimous versus majority split treats observed agreement as if it were a property of the post, and section 3 explains why it is not. The goal of this proposal is a set of experiments, all runnable on data we already have, that separate real boundary content from the other things that produce a split vote.

## 2. Motivating questions

1. How much of the observed unanimous versus split distinction is small-sample noise, given that most posts have only 3 or 4 raters?
2. Of the disagreement that is not noise, how much is rater-driven (some raters remove more than others, or apply different rules) versus post-driven (the post itself sits near a shared boundary)?
3. Is post-driven ambiguity predictable from the text, and if so, what does the language of the boundary look like?
4. Does human ambiguity explain model errors, and can an ambiguity score buy us practical gains, such as knowing when to trust the model and which posts to oversample in the next data collection?

## 3. The measurement problem we have to solve first

Observed unanimity is confounded with the number of raters. A post rated by 3 people goes unanimous whenever all 3 agree, which happens often by chance even when the underlying population is split. A post rated by 9 people almost never goes unanimous. The current data shows exactly that pattern.

| Raters per post | Posts | Share unanimous |
| ---: | ---: | ---: |
| 3 | 1,796 | 50.7% |
| 4 | 1,086 | 42.8% |
| 5 | 539 | 33.0% |
| 6 | 298 | 18.8% |
| 7 | 141 | 14.9% |
| 8 to 14 | 133 | ~10% |

So "unanimous at 3 raters" is weak evidence that a post is a clear case, and "split at 3 raters" is weak evidence that it is a boundary case. If we imagine each post has some true removal probability in the population, a post where 70% of people would vote keep still draws exactly one dissenting remove vote about 44% of the time with 3 raters. The four cells we have been using are therefore contaminated in both directions, and we do not currently know by how much. Estimating that contamination is the first job.

The prior analysis also excluded the very center of the boundary, because the four-cell cohort dropped the 275 posts with an exact tie, and tied posts are the most disagreed-on posts by definition.

Model errors already line up with the vote margin as well. A quick join of the existing Qwen3 Next 80B correctness labels ([`model_errors_analysis_2026_07_15`](../model_errors_analysis_2026_07_15/)) onto the four-cell cohort shows that the model's error rate rises as the human vote gets closer.

| Human vote pattern (posts with 3 or more raters) | Posts | Model error rate |
| --- | ---: | ---: |
| Unanimous | 1,644 | 27.6% |
| Lopsided split (minority share under about a quarter) | 773 | 37.0% |
| Close split | 1,301 | 42.6% |
| Of which, majority keep cell | 1,480 | 49.7% |
| Of which, unanimous remove cell | 154 | 8.4% |

Already in the raw data, the model's misses concentrate where humans disagree. The proposal below turns that observation into evidence about what the disagreement is made of.

## 4. What "ambiguous" can mean, and why we must tell the cases apart

A split vote on a post can come from four different sources, and each source calls for a different response.

1. **Sampling noise.** Too few raters were drawn. The population would mostly agree, but our 3 draws happened to split. The fix is more raters, not a theory of the boundary.
2. **Rater severity.** Raters have stable personal thresholds. A lenient rater paired with a strict rater splits on many posts that neither finds hard. The disagreement is real but tells us about people, not about the post.
3. **Criterion conflict.** Raters hold different stated rules. For example, the free-response mining found a "harm threshold within free speech" group and a "remove for toxicity" group. Two such raters can each be confident and still disagree on a specific class of posts. The disagreement is systematic, and it maps a fault line between moderation philosophies rather than a fuzzy boundary.
4. **Genuine boundary content.** The post sits near a threshold that most raters share, so individual raters are themselves uncertain. Genuine boundary content is the case the writeup cares most about, the grey zone of posts that are emotional and moralized yet kept by a majority.

The experiments below are chosen so that each source shows up differently in the data. Noise shrinks under resampling checks. Severity shows up as rater main effects in a joint model. Criterion conflict shows up as interactions between rater groups and post types, and in the free text. Genuine boundary content is what remains after adjusting for the first three, and it should show up in behavior, for example as slower decisions, and should be predictable from the text.

## 5. Data we already have

All of the following exists locally in the repo or in existing experiment outputs, so every experiment in this proposal runs on current data.

- Per-trial records for 23,560 linked-fate keep/remove decisions, with `participant_id`, `post_id`, `decision`, `response_time_ms` on every trial, and trial order within the session (`shared/data/raw/study_phase_2_part_2/results/full.csv`).
- Per-rater covariates joinable on `participant_id`, including party affiliation, ideology, demographics, six issue-attitude items, the 1 to 7 linked-fate influence rating, and the free-text reflection.
- Per-post stimulus fields, including original and mirror text, stance (`sampled_stance`), and the three-way toxicity stratum (`sample_toxicity_type`).
- 3,993 posts with 3 or more raters, including the 275 tied posts that earlier work dropped, and 2,411 single-rater plus 2,387 two-rater posts that can serve as held-out text for predictive checks.
- Titan embeddings for 8,790 posts and BERTopic topic assignments for the corpus.
- Stage 1 LLM features covering the full 3,718-post four-cell cohort.
- Qwen3 Next 80B correctness labels for all 8,791 posts, the prompt-tuned and control LLM predictions on the balanced 1,000-post subset, and the two LoRA fine-tune splits and predictions.
- The mined free-response decision-rule clusters, split by influence rating.

There is one known gap to check before use. Some Stage 1 LLM features were generated by prompts that told the model the human outcome, which leaks the label. Before any experiment uses those features to predict agreement, we will audit the generation prompts and either regenerate the affected features blind or restrict to feature families that do not encode the label.

## 6. Proposed experiments

Each experiment below states its purpose, a sketch of the method, and what we hope it gives. Detailed designs come later, one experiment at a time, after this proposal is approved.

### E1. Noise floor and a continuous ambiguity score

**Purpose.** Answer question 1. Replace the four cells with a per-post estimate of the underlying removal probability, with honest uncertainty, and quantify how contaminated the current cells are.

**Method sketch.** Fit a beta-binomial model to the per-post keep/remove counts. A beta-binomial model treats each post as having its own true removal probability drawn from a population distribution, and it uses all posts jointly to estimate that distribution. Each post then gets a shrunk removal probability estimate and a posterior probability of lying in a middle band (for example, true removal probability between 0.25 and 0.75). Validate the model with resampling checks on the posts that have many raters. For posts with 6 or more raters, split the raters into random halves and ask how well one half's vote predicts the other half's vote. Also simulate the four-cell assignment under the fitted model to estimate what fraction of, say, majority keep posts at 3 raters are actually clear-keep posts that drew one noisy vote.

**What it gives.** E1 gives a continuous ambiguity score with an uncertainty estimate for every post, and every later experiment can consume that score. It also gives the first concrete number for what share of the majority cells is noise, which directly informs how many raters per post the 20k collection should use.

### E2. Rater severity and residual disagreement

**Purpose.** Answer question 2. Split disagreement into a rater part and a post part.

**Method sketch.** Fit a crossed model of individual decisions, where the log-odds that rater j removes post i is the sum of a post removability term and a rater severity term. The structure is the same as an item response model in psychometrics, and it is estimable here because raters each did 20 posts and posts have overlapping rater sets. Report the variance attributable to raters versus posts. Then recompute each post's ambiguity after removing rater severity, and see which posts move. As a targeted extension, add an interaction between rater party and post stance to test whether any residual partisanship survives the linked-fate procedure and contributes to splits, which the study design predicts it should not.

**What it gives.** E2 gives an adjusted ambiguity score that is about the post rather than about who happened to rate it, plus a decomposition we can cite, such as "X% of split votes are explained by rater severity alone." If the interaction between party and stance is near zero, that result is also a new confirmation of the core linked-fate claim at the level of individual decisions.

### E3. Response time as a behavioral check

**Purpose.** Test whether posts we call ambiguous are hard for the individual rater, not just disagreed on across raters. Raters could disagree even if every rater is instantly confident, which is what criterion conflict looks like, so decision time is an independent signal that distinguishes internal uncertainty from confident disagreement.

**Method sketch.** Model per-trial response time as a function of the post's ambiguity score from E1 and E2, controlling for text length (reading time), trial position in the session (practice effects), and rater identity. Add two supporting contrasts. The first compares minority voters on split posts against majority voters on the same posts. The second examines response time on tied posts, which the prior analysis never looked at.

**What it gives.** If adjusted ambiguity predicts slower decisions after controls, we have behavioral evidence that the boundary band reflects genuine individual uncertainty. If split posts are decided quickly, the evidence points instead toward criterion conflict, and E4 becomes the central experiment. Either way we learn what the grey zone is made of.

### E4. Stated rules and who disagrees with whom

**Purpose.** Test the criterion-conflict explanation directly using what participants said they were doing.

**Method sketch.** Join each rater's mined decision-rule cluster (from the free-response mining, for example "harm threshold within free speech" versus "remove for threats and toxicity") and their influence rating to their individual votes. Ask two things. First, do raters from different rule groups have different severities, in the E2 sense? Second, on posts where two raters disagreed, are the disagreeing pairs drawn from different rule groups more often than chance? Then look at which kinds of posts specific pairs of rule groups split on.

**What it gives.** If disagreement concentrates in specific pairs of rule groups on specific content, ambiguity is partly a conflict between stated moderation philosophies, which is a substantively different finding from "the post is fuzzy," and it suggests the 20k collection should measure rater philosophy up front. If rule groups do not predict disagreement, the free-text clusters are stories told after the fact, which is also worth knowing before we lean on them in the writeup.

### E5. Is ambiguity written in the text?

**Purpose.** Answer question 3. If genuine boundary content exists, the adjusted ambiguity score should be predictable from the post text, above what the keep/remove label itself explains, and the predictive features should describe the boundary language.

**Method sketch.** Train simple predictors (logistic or gradient-boosted models on Titan embeddings, the shared surface features, and audited Stage 1 LLM features) for two distinct targets, the modal label and the adjusted ambiguity score. Compare which features carry each target. Then test the writeup's specific grey-zone hypothesis as a contrast specified in advance, namely that posts high on moral and emotional language but without profanity, slurs, or direct personal attack sit disproportionately in the boundary band. Use the posts with only 1 or 2 raters as a genuinely held-out set for the text model, since they never enter the ambiguity estimation.

**What it gives.** E5 gives a yes or no on whether ambiguity is a property of the post at all, and if yes, a concrete description of boundary language to put alongside the existing lists of keep features and remove features. The contrast between features that predict the label and features that predict the ambiguity is the cleanest way to describe what sets the grey zone apart.

### E6. Model difficulty, calibration, and knowing when to abstain

**Purpose.** Answer question 4. Turn the section 3 pilot observation into a proper analysis, and extract the practical payoff.

**Method sketch.** The method has three parts. The first is calibration, comparing model-predicted removal probabilities (from the existing prompt runs, and from fresh runs that sample the same open model several times where log-probabilities or vote sampling are available) against the human vote share rather than just the modal label. The second is ensemble disagreement, scoring each post by the disagreement among model variants we already ran (control prompt, tuned prompt, the two fine-tunes) and testing how well model disagreement predicts human disagreement. The third is selective prediction, plotting accuracy against coverage when the model abstains on the top k% most ambiguous posts, using each candidate ambiguity score (raw margin, E1 score, E2 adjusted score, model ensemble score) so the scores compete on a practical task.

**What it gives.** E6 gives evidence for or against the writeup's claim that the model's misses are the humans' grey zone. It also makes ambiguity useful in practice, since an abstention curve tells us exactly how much accuracy is recoverable by routing boundary posts to more raters, and the score comparison tells us which definition of ambiguity to standardize on going forward.

### E7. Close reading of the center

**Purpose.** Check the quantitative scores against a human reading, and surface hypotheses the pipelines miss.

**Method sketch.** Run a structured qualitative audit of three small samples. The first sample is the 275 tied posts that prior work dropped. The second is the posts with the highest adjusted ambiguity among posts that many raters saw, meaning 6 or more raters and a near even split. The third is the posts the E1 model most strongly reclassifies, for example posts unanimous at 3 raters whose shrunk estimate lands near the middle. Read them against the four-source taxonomy in section 4 and tag which explanation fits.

**What it gives.** E7 gives ground truth on whether our scores pick out posts a human reader also finds contestable, plus concrete example posts for the writeup. The effort is small and the interpretive value is high.

## 7. Ablations and robustness checks

The checks below apply across experiments rather than being experiments of their own.

- Ambiguity definitions. Compare raw minority share, vote entropy, the E1 posterior band probability, and the E2 adjusted score. Report main results under each so no finding depends on one arbitrary definition.
- Rater-count thresholds. Repeat key results on posts with at least 3, at least 4, and at least 5 raters, since composition changes with the threshold.
- Text scope. Compare original text only against original plus mirror text, the same choice the four-cell analysis already had to make.
- Ties in or out. Prior work excluded ties. Every analysis here includes them, with a sensitivity check excluding them.
- Assignment mechanism check. Verify that how many raters a post received is unrelated to its content, as the session sampler should guarantee, since E1 assumes the rater count carries no information about the post.

## 8. What the outcomes would mean

The experiments are chosen so that each possible result points to a different next action.

- If E1 says most split votes are sampling noise, the grey zone is smaller than it looks, and the 20k collection should prioritize more raters per post over more posts.
- If E2 and E4 say disagreement is mostly rater severity or rule conflict, the boundary is between people, not in the posts. The next collection should measure rater philosophy directly, and the modeling target should become predictions conditioned on the rater rather than one consensus label.
- If E3 and E5 say a residual post-driven boundary band exists, is slow to judge, and is predictable from text, then the grey zone is a real object. We can then characterize its language, oversample it in the next collection, and build the abstention policy from E6 into the classifier evaluation.
- Most likely all three components exist. The deliverable in that case is the decomposition itself, with each post carrying a score and each component sized, which is the concrete evidence the writeup currently lacks.

## 9. Order of work

E1 and E2 come first because their scores feed E3, E5, E6, and E7. E3 and E4 can run in parallel once E2 exists, since they only need the fitted rater and post terms plus existing per-trial data. E5 and E6 follow, and E7 runs last so the close reading can use the final scores. The only new compute beyond fitting small statistical models is the optional repeated-sampling LLM runs in E6 and the possible blind regeneration of leaked Stage 1 features in E5, and both reuse existing pipelines.

## 10. Risks and limits

- We cannot measure within-rater instability directly, because no rater judged the same post twice. Response time is our best available proxy for individual uncertainty, and it is an imperfect one.
- Response times carry confounds, such as reading speed, fatigue, and interface effects. The controls in E3 reduce these confounds but cannot remove them, so E3 is treated as supporting evidence, not the primary test.
- The free-response rule clusters cover only the coherent subset of reflections, and the mining dropped a large noise share, so E4 has reduced power and its null is less informative than its positive.
- Toxicity strata are three-way sampling strata, not continuous scores, so toxicity can only be controlled coarsely.
- With a median of 3 raters per post, per-post estimates lean on the population distribution. The shrinkage in E1 exists for exactly that reason, but it means claims about single posts stay uncertain, and the strong claims should be about strata and scores, not individual posts.
