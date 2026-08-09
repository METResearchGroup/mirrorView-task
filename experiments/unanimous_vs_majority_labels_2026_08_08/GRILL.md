# Results from grilling session with AI

Results from `/grill-me` session with the AI.

Claim
Primary: Unanimous keep/remove sit in clearer, more extreme content regions than strict-majority keep/remove; disagreement concentrates in mid-toxicity, shorter, more arguable posts.
Secondary: “Threshold violations vs political disagreement” — tested descriptively via toxicity + stance (not the headline).
Method: Descriptive only (no tests/CIs).
Cohort
Slim linked-fate trials, n_raters >= 3.
4 cells: unanimous keep, majority keep, majority remove, unanimous remove.
Exact ties excluded (not analyzed).
Cohort is experiment-local (not a new shared registry dataset).
Expected sizes: ~1,490 / 1,480 / 594 / 154.
Text & joins
Analyses 1 & 3 (and length/toxicity gradients): original_text only.
Toxicity strata: sample_toxicity_type ∈ {low, middle, high}.
Stance: sampled_stance ∈ {left, right} from stimuli.
Analysis 1 (full surface set on originals)
Length/structure: char, word, sentence counts; avg sentence length; punctuation density.
Readability: Flesch–Kincaid grade; reading ease.
Classifiers via shared/textual_features/: valence, intergroup, PRIME (prestige / in-group / moral / emotional).
Report by cell (descriptive summaries; continuous metrics in the same spirit as your existing median length gradient).
Analysis 2 (LLM features → clouds)
Stage 1 only from create_llm_features lineage (no embed/cluster/label).
Cover all 4-cell posts; reuse existing Stage-1 rows for overlapping message_ids; generate only missing IDs via a thin adapter in this experiment; don’t mutate old experiment outputs.
Keep the dual-text prompt (original + mirror) for feature extraction parity with reused rows.
Word clouds: tokenize feature_value (all categories) → stopwords / punctuation / low-content tokens (none, in, …) → post-level binary document frequency → light scrub of meta tokens (mirror, original, …).
Deliverables: 4 clouds + top-N token tables per cell (N≈30).
Analysis 3
Three 2×4 tables: sampled_stance (left/right) × 4 cells, one table per toxicity stratum.
Out of scope
Ties; formal inference; rater_agreement_2026_08_06; Stages 2–4 clustering; shared-catalog majority dataset; strategy-doc writeup.
Done bar
Working scripts under this experiment.
Rewritten README matching this design.
RESULTS.md + outputs/ figures/tables for the above.
