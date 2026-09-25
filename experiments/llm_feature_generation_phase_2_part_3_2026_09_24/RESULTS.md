# LLM feature generation, Phase 2 Parts 2 and 3

## Summary

The approved codebook has 30 features. Each of 20,000 posts was labeled on its original text and its mirrored text (40,000 labels, 0 failures). Statistical tests use the held-out half only: 10,001 posts. The outcome is the modal keep/remove label from all raters. Discovery used gpt-6-luna with reasoning off. Recorded spend is $12.11, under the $25 cap. Batch labeling is priced at half the standard rate and the cost log does not subtract prompt-cache discounts, so the bill can be lower than this figure.

Logistic models use a derived neutral-direct-address feature (direct address and not confrontational address) in place of raw `cb_027`, because confrontational address is a subset of direct address.

## Caveats

- Labels are provisional LLM labels without human validation.
- Part 2 themes were named by gpt-5.4-nano. This codebook was named and labeled by gpt-6-luna. A Part 2 comparison mixes a model change with a data change.
- A self-consistency re-label of 200 texts (seed 42) had mean agreement 95.0%. Four features fell below 90% and were kept: cb_007 (unqualified factual claims, 88.0%), cb_017 (hostile group division, 88.5%), cb_018 (explicit causal claims, 89.5%), cb_023 (colloquial language and insults, 87.0%).
- Original-versus-mirror agreement is reported as a rate. The analysis file also stores a Benjamini-Hochberg value computed from `1 - agreement`. That is not a hypothesis test, so it is not used below.
- Batch-design, clustering-method, and seed ablations were not re-fit. There is one approved codebook, built from the mixed discovery run plus the union top-up, HDBSCAN, seed 42.
- The party-by-stance table is descriptive. It is the share of posts in each cell where the feature is present. It is not a tested interaction.

## Q1. Which features go with remove?

On the 10,001 held-out posts, 14 features are more common on remove posts and 10 are more common on keep posts (Benjamini-Hochberg q < 0.05). 6 features are not distinguishable. Rates are the share of original texts where the feature is present.

| name | keep | remove | diff | q |
| --- | --- | --- | --- | --- |
| intense political outrage | 13.8% | 54.0% | +40.2 pp | <1e-300 |
| political insults | 24.2% | 64.3% | +40.2 pp | 1.27e-288 |
| profane derogatory insults | 9.9% | 42.6% | +32.7 pp | 1.15e-292 |
| colloquial language and insults | 46.7% | 77.4% | +30.7 pp | 7.16e-153 |
| political actor criticism | 61.5% | 86.7% | +25.2 pp | 1.15e-116 |
| hostile group division | 25.5% | 46.5% | +21.1 pp | 1.50e-84 |
| explicit moral judgment | 42.7% | 63.6% | +20.8 pp | 8.47e-71 |
| sarcasm and mockery | 20.7% | 37.6% | +16.9 pp | 1.29e-62 |
| persuasive argumentation | 26.6% | 13.8% | -12.8 pp | 7.76e-38 |
| unqualified factual claims | 64.6% | 53.7% | -10.9 pp | 2.09e-21 |
| specific policy advocacy | 22.5% | 12.3% | -10.1 pp | 6.11e-27 |
| contrastive framing | 53.1% | 44.8% | -8.3 pp | 2.54e-12 |
| confrontational direct address | 11.5% | 19.1% | +7.6 pp | 3.02e-21 |
| explicit causal claims | 29.2% | 21.9% | -7.4 pp | 3.26e-12 |
| left right partisan framing | 34.4% | 41.1% | +6.7 pp | 3.87e-09 |
| qualified claims | 17.0% | 11.5% | -5.5 pp | 2.55e-10 |
| emphatic typography | 11.9% | 17.1% | +5.2 pp | 9.21e-11 |
| lists of related points | 11.8% | 7.4% | -4.4 pp | 2.27e-09 |
| direct second person address | 20.7% | 24.8% | +4.1 pp | 3.27e-05 |
| anti-elite framing | 8.6% | 4.9% | -3.6 pp | 1.14e-08 |
| violent political rhetoric | 0.9% | 3.9% | +3.0 pp | 3.73e-24 |
| personal political distress | 5.0% | 8.0% | +3.0 pp | 9.50e-08 |
| conditional reasoning | 14.3% | 11.9% | -2.3 pp | 5.07e-03 |
| political calls to action | 14.2% | 12.3% | -1.8 pp | 2.97e-02 |
| quoted attributed speech | 14.9% | 13.6% | -1.3 pp | 1.42e-01 |
| group persecution framing | 9.4% | 8.2% | -1.2 pp | 1.00e-01 |
| hashtags and account mentions | 3.7% | 2.8% | -0.9 pp | 5.38e-02 |
| conspiracy allegations | 3.8% | 3.1% | -0.7 pp | 1.14e-01 |
| rhetorical questions | 11.7% | 12.2% | +0.5 pp | 5.03e-01 |
| parallel repetition | 9.1% | 8.6% | -0.5 pp | 4.79e-01 |

The largest remove gaps are profane insults, political insults, intense outrage, and colloquial insults. The largest keep gaps are persuasive argumentation, specific policy advocacy, contrastive framing, and lists.

### Part 2 catalog, Part 3 raters only

4449 held-out posts are in the Part 2 stimulus catalog. Their modal label here uses Part 3 raters only. 22 features are significant in both this subset and the full test set. Features significant only on the full test set: conditional reasoning, direct second person address. Features significant only on the catalog subset: group persecution framing, hashtags and account mentions.

## Q2. Original versus mirror agreement

Agreement is the share of held-out posts where the original label and the mirror label match. 14 of 30 features agree on at least 90% of posts. The lowest agreement:

| Feature | Agreement |
| --- | --- |
| explicit moral judgment | 70.8% |
| hostile group division | 71.0% |
| contrastive framing | 74.3% |
| left right partisan framing | 75.9% |
| explicit causal claims | 77.3% |
| unqualified factual claims | 77.4% |
| colloquial language and insults | 79.2% |
| political actor criticism | 81.1% |

Hostile group division and explicit moral judgment move the most when the text is mirrored. Rare features (hashtags, violent rhetoric, personal distress) agree most, largely because both texts are usually absent.

## Q3. Which direction does the flip go?

Each rate is the share of held-out posts with the feature on one surface and off the other. The eight largest absolute gaps:

| Feature | Original only | Mirror only |
| --- | --- | --- |
| hostile group division | 4.3% | 24.7% |
| left right partisan framing | 2.3% | 21.8% |
| unqualified factual claims | 4.7% | 17.9% |
| political actor criticism | 2.9% | 15.9% |
| explicit moral judgment | 8.5% | 20.7% |
| contrastive framing | 7.8% | 17.9% |
| anti-elite framing | 2.7% | 12.7% |
| explicit causal claims | 6.8% | 16.0% |

## Q4. Predicting keep versus remove

Logistic regression on the held-out posts. `paired` uses both surfaces. `combined` uses only the original-minus-mirror difference for each feature.

| Model | AUC | Log loss |
| --- | --- | --- |
| original only | 0.808 | 0.392 |
| mirror only | 0.794 | 0.401 |
| paired | 0.820 | 0.382 |
| difference only | 0.609 | 0.485 |

Original features predict the modal decision slightly better than mirror features. Adding the mirror features improves AUC a little. The difference features alone are weak: the flip is not what carries the keep/remove signal.

## Q5. Disagreement

Three-group labels need at least four raters. On the held-out half that is 5372 posts: 2558 unanimous keep, 2610 split, 204 unanimous remove. Feature rates on the original text, for the ten largest gaps between unanimous remove and unanimous keep:

| Feature | Unanimous keep | Split | Unanimous remove |
| --- | --- | --- | --- |
| intense political outrage | 5.0% | 34.1% | 85.3% |
| political insults | 12.3% | 48.1% | 84.3% |
| profane derogatory insults | 3.1% | 26.7% | 68.6% |
| colloquial language and insults | 33.8% | 66.4% | 87.7% |
| political actor criticism | 48.2% | 79.9% | 92.6% |
| hostile group division | 17.6% | 39.3% | 57.8% |
| explicit moral judgment | 35.0% | 55.7% | 73.5% |
| unqualified factual claims | 65.4% | 60.5% | 35.8% |
| sarcasm and mockery | 13.3% | 31.3% | 39.7% |
| persuasive argumentation | 32.3% | 18.3% | 8.3% |

## Q6. Party, stance, and feature

The saved table has one row per moderator party, post stance, and feature. The value is how often the feature is present on those posts among remove-labeled trials. It does not test an interaction. Read it as a description, not a significance result. The file is `outputs/paired/analysis/2026-09-25T03-21-46/q6_party_interaction.csv`.

## Q7. Value beyond toxicity and stance

A model with toxicity bucket and sampled stance has AUC 0.750 (log loss 0.421). Adding the original-text features raises AUC to 0.819 (log loss 0.384), a gain of 0.070.

## Part 2 theme map

Each feature is matched to the nearest Part 2 theme by Titan cosine similarity. The match is provisional. Similarity is modest: the best is 0.79 and the worst is 0.25. Themes with no codebook feature as their nearest match are not recovered here. The full table is `outputs/shared/part2_theme_map/2026-09-24T16-41-04/theme_map.csv`.

| feature_name | part2_theme_label | cosine |
| --- | --- | --- |
| political calls to action | Call to action / political participation and collective mobilization | 0.79 |
| direct second person address | Second-person direct address and personal blame | 0.78 |
| explicit causal claims | Causal claims that link policy/actors to harms or outcomes | 0.76 |
| profane derogatory insults | Profanity / taboo insults / dehumanizing labels | 0.74 |
| sarcasm and mockery | Ridicule / mockery via rhetorical questions, sarcasm, and contemptuous evaluation | 0.71 |
| specific policy advocacy | Policy advocacy for rights/legislation (non-punitive) | 0.69 |
| political insults | Profanity / taboo insults used in political disagreement | 0.69 |
| quoted attributed speech | Quoted speech / attribution blocks and slogan-like embedded statements | 0.66 |
| group persecution framing | Victimhood/persecution framing and harm-to-innocents rhetoric | 0.62 |
| confrontational direct address | Direct address / imperative discourse to the reader | 0.61 |
| rhetorical questions | Rhetorical questions and question-based confrontation | 0.61 |
| intense political outrage | Emphatic outrage and absolute condemnation (intensifiers, punchy judgments) | 0.60 |
| conspiracy allegations | Conspiracy and hidden-plot explanations | 0.60 |
| violent political rhetoric | Violence/violent threat or lethal-force advocacy | 0.58 |
| contrastive framing | Outgroup vs ingroup framing (us-vs-them / “your side” contrasts) | 0.57 |
| anti-elite framing | Us-vs-them / antagonistic framing by political bloc | 0.56 |
| hashtags and account mentions | Attribution-heavy political naming (proper nouns, handles, institutions) | 0.56 |
| left right partisan framing | Partisan in-group/out-group framing and mirror blame shifts | 0.55 |
| emphatic typography | All-caps / emphatic formatting and high emotive punctuation | 0.53 |
| colloquial language and insults | Profanity and taboo/informal insults | 0.51 |
| persuasive argumentation | Non-violent argumentative framing: evidence, conditionals, or normative persuasion | 0.48 |
| hostile group division | Outgroup vs ingroup “us vs them” or militant boogeyman framing | 0.45 |
| conditional reasoning | Conditional / causal claims about political outcomes and consequences | 0.44 |
| explicit moral judgment | Normative moral language about rights, fairness, and harm | 0.41 |
| qualified claims | Conditional / causal claims about political outcomes and consequences | 0.39 |
| personal political distress | Policy conflict framed as “rigging/corruption/warmongering” against opponents | 0.38 |
| unqualified factual claims | Conditional / causal claims about political outcomes and consequences | 0.35 |
| political actor criticism | Attribution-heavy political naming (proper nouns, handles, institutions) | 0.34 |
| parallel repetition | Mirror/rebuttal shift: critique mirrored onto another target while reusing structure | 0.34 |
| lists of related points | Causal / blame-evidence chains (cause-effect claims, “X led to Y”) | 0.25 |

## What this does not answer

- Whether a person would mark the same features. There is no human validation.
- Whether a different discovery batch design, clustering method, or seed would yield a different codebook. Those ablations were not re-run after the codebook was approved.
- A tested party-by-stance interaction. Q6 is descriptive.
- A clean comparison with Part 2 theme effects. The theme link is nearest-neighbor similarity, and the naming model changed.
