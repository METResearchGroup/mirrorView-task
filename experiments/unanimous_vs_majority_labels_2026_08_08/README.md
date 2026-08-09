# Unanimous vs. majority labels, 2026-08-08

We want to see if there's a tangible difference between posts that are rated unanimously vs. posts that have a majority label. Right now, it seems like the cleanest takeaway is "Consensus appears at the clearest ends of the moderation spectrum; disagreement concentrates around rhetorically “hot” but substantively arguable boundary cases."

We'll split posts into two groups:

- unanimous
- majority-labeled (not unanimous)

Current counts:

- Unanimous keep: 1,490
- Unanimous remove: 154
- Strict-majority keep: 1,480
- Strict-majority remove: 594
- Exact ties: 275 (we'll keep these separate)

Each will have either keep or remove labels. This creates a 2x2 separation, between unanimous keep/remove and majority-labeled keep/remove.

Strong preliminary signal:

A quick descriptive comparison of the four strict cells shows a nearly monotonic toxicity gradient:

- Unanimous keep: 4.6% high toxicity
- Majority keep: 19.2% high toxicity
- Majority remove: 52.5% high toxicity
- Unanimous remove: 70.8% high toxicity

Median original-post length similarly declines:

- Unanimous keep: 203 characters
- Majority keep: 184
- Majority remove: 146
- Unanimous remove: 132

Right now, what it seems like is "unanimous removal is driven by stacked, explicit threshold violations rather than political disagreement itself."

## Analysis 1

Some things we want to look at include:

- Character, word, and sentence counts
- Average sentence length
- Punctuation density
- Flesch–Kincaid grade
- Reading ease
- Valence
- Intergroup discussion
- PRIME cues: prestige, in-group, moral, emotional

## Analysis 2

We'll also re-use the [previously generated features](../create_llm_features_2026_08_05/). For each of the 4 cells, we'll generate a word cloud of the most commonly mentioned key topical words and features.

## Analysis 3

Lastly, we'll pull the raw data, from `STUDY_PHASE_2_PART_2_STIMULI`, and compare the `sampled_stance` against the 4-cell matrix and report a table with two rows (left/right) and 4 columns (unanimous keep, majority keep, majority remove, unanimous remove).

## Actual steps

Steps:

1. Get datasets. ...
...
