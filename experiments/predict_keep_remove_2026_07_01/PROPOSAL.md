# Proposal: Predict Keep/Remove Actions

## Purpose

This experiment should reuse the useful structure from `experiments/predict_keep_remove_2026_05_07/`, but adapt it to the larger June 2026 study results in `keep_remove_results_2026_06_23.csv`.

The goal is not just to train the strongest possible classifier. The useful outcome is an experiment ladder that tells us:

- how predictable keep/remove decisions are from the new study data;
- how much performance comes from trivial priors, text-pair information, participant/context features, and engineered features;
- whether explainable, reproducible features can approach embedding or model-derived performance;
- how performance scales with training data size.

## What We Did In The May Experiment

The May experiment established a first keep/remove modeling pipeline around linked-fate moderation rows.

Core setup:

- Target: binary keep/remove decision, encoded as `keep_remove_label`, with `1=remove` and `0=keep`.
- Data filter: only linked-fate rows with valid `keep` or `remove` decisions.
- Initial split: random row split with `train_split=0.8` and `seed=42`.
- Feature set: analysis-derived labels and text statistics for both original and mirror texts, plus linked-fate context features.
- Models: logistic regression and XGBoost.
- Outputs: timestamped folders with model artifacts, metrics, predictions, metadata, feature coefficients/importances, and calibration artifacts.

The non-embedding feature set included:

- intergroup classifier labels for original and mirror text;
- PRIME classifier labels for original and mirror text;
- valence labels for original and mirror text;
- length/compression metrics for original and mirror text;
- readability metrics for original and mirror text;
- contextual categorical variables such as toxicity type and stance.

The May run also added three important supporting pieces:

- Baselines: always keep, always remove, and stratified random from the training prior.
- Calibration: train/calibration/test split, probability calibration, threshold sweep, and remove-focused threshold selection.
- Embedding plan/pipeline: precompute embeddings for original and mirror text, cache by text hash, and join embeddings back to row-level decisions.

The strongest May tabular model was XGBoost by ROC-AUC, but both logistic regression and XGBoost had modest remove recall at the default threshold. That made the calibration/thresholding work important: raw accuracy was not enough because the task was keep-heavy and the decision of interest was usually remove.

## Key Lessons To Carry Forward

The new experiment should preserve these principles:

- Treat `remove` as the positive class for primary reporting.
- Report class balance before model performance.
- Always compare against trivial baselines.
- Do not rely on default threshold `0.5`; select thresholds on a held-out validation/calibration split.
- Save predictions, not just aggregate metrics, so errors can be inspected later.
- Keep output folders timestamped and self-describing with metadata.

The new experiment should improve on the May setup in one important way:

- Primary evaluation should use grouped splits, not random row splits, if the same post/pair can appear multiple times. Random row splits are useful as a diagnostic, but they can overstate generalization if near-identical text pairs appear in both train and test.

## Proposed July Experiment Design

### Data Unit And Target

Start by making the data contract explicit.

Expected source:

- `keep_remove_results_2026_06_23.csv`

Expected modeling row:

- one participant decision for one original/flip pair;
- includes enough identifiers to group by participant and by post/pair;
- includes original text, flipped/mirror text, and the keep/remove decision.

Target:

- `keep_remove_label = 1` for remove;
- `keep_remove_label = 0` for keep.

Before training, create a data summary that answers:

- how many rows are available;
- how many unique participants;
- how many unique posts or text pairs;
- keep/remove class balance overall;
- class balance by condition, stance, toxicity type, or other available study fields;
- duplicate structure: repeated posts, repeated flips, repeated users, and repeated text pairs.

This summary should determine the final split policy and which metadata fields are useful as features.

### Evaluation Splits

Use one primary split and a small set of diagnostic splits.

Primary split:

- Group by post or text-pair identifier.
- Purpose: estimate performance on unseen content.
- Recommended shape: train/calibration/test, e.g. `64/16/20`.

Diagnostic splits:

- Group by participant, if the question is whether the model generalizes to unseen users.
- Random row split, only as an optimistic diagnostic and for comparison with the May experiment.

If there are multiple decisions per post/pair, avoid allowing the same text pair into both train and test for the primary result.

### Metrics

Primary metrics should be remove-focused:

- precision_remove;
- recall_remove;
- f1_remove;
- PR-AUC for remove;
- balanced accuracy.

Secondary metrics:

- accuracy;
- ROC-AUC;
- calibration quality, such as Brier score and reliability bins/curves.

Every model report should include:

- class balance;
- baseline comparison;
- default-threshold metrics;
- selected-threshold metrics;
- test predictions with probabilities.

## Experiment Ladder

Run models in increasing complexity. Each stage should answer a specific question before moving on.

### Stage 0: Data Audit And Baselines

Purpose:

- establish the target distribution and trivial benchmark performance.

Run:

- always keep;
- always remove;
- stratified random using the train prior;
- optional participant- or condition-specific priors if the data supports them.

Decision gate:

- confirm class balance and split integrity;
- define the minimum useful lift over trivial baselines.

### Stage 1: Simple Tabular Models On Available Metadata

Purpose:

- test how much signal exists in study metadata and easy-to-compute fields before expensive feature extraction.

Candidate inputs:

- condition;
- stance;
- toxicity type;
- participant-level fields if available and appropriate;
- simple text lengths and pair-level deltas.

Models:

- logistic regression;
- XGBoost or another tree-based model.

Decision gate:

- establish a reproducible baseline with interpretable coefficients/importances;
- identify whether metadata alone is predictive enough to matter.

### Stage 2: Text Pair Embedding Models

Purpose:

- estimate the ceiling from semantic text-pair information.

Inputs:

- embedding(original text);
- embedding(flipped/mirror text);
- optional absolute difference and elementwise product between embeddings;
- optionally concatenate metadata from Stage 1.

Models:

- embeddings plus logistic regression;
- embeddings plus XGBoost or light MLP;
- hybrid metadata plus embeddings model.

Decision gate:

- decide whether semantic representation substantially improves over tabular baselines;
- use this as the main performance reference for later explainable feature work.

### Stage 3: Feature Extraction For Explainability

Purpose:

- build reproducible, inspectable features that explain why users keep or remove a pair.

Candidate feature families:

- original and flip length/readability/compression metrics;
- toxicity, sentiment, valence, stance, or intergroup labels;
- pairwise deltas, such as toxicity_delta, sentiment_delta, length_delta, readability_delta;
- structural features, such as whether the flip softens, intensifies, reframes, or changes target group language;
- user/context interactions, if relevant.

Models:

- logistic regression for interpretability;
- XGBoost for nonlinear interactions;
- calibration and thresholding for both.

Decision gate:

- compare feature-only performance against embedding-based performance;
- inspect top features and error modes;
- decide which feature families are worth formalizing.

### Stage 4: Scaling Curves

Purpose:

- estimate whether more labeled decisions are likely to improve performance.

Run the strongest representative models from earlier stages across increasing training set sizes:

- small fractions, such as 5%, 10%, 25%, 50%, 75%, 100%;
- repeat over multiple seeds or folds if feasible;
- keep validation/test fixed for comparability.

Report:

- mean and variance for primary remove-focused metrics;
- learning curves for PR-AUC, f1_remove, and recall/precision tradeoff;
- whether performance is still data-limited at full training size.

Decision gate:

- decide whether the next investment should be more data, better features, better model class, or better label/problem formulation.

## Recommended Order Of Operations

1. Place and validate `keep_remove_results_2026_06_23.csv`.
2. Write a lightweight data audit that confirms schema, row counts, identifiers, class balance, and duplicate structure.
3. Define the canonical modeling dataframe and target encoding.
4. Choose the primary grouped split and one or two diagnostic split modes.
5. Run Stage 0 baselines on the selected splits.
6. Train Stage 1 simple metadata/text-stat models.
7. Add calibration and threshold selection once at least one nontrivial model is working.
8. Build the embedding cache and run Stage 2 embedding models.
9. Design and compute explainable feature families for Stage 3.
10. Run scaling curves using the most informative models from Stages 1 to 3.
11. Summarize results in one comparison table and a short decision memo.

## Suggested Folder Shape

Keep the July experiment self-contained and parallel to the May experiment:

- `dataloader.py`: source CSV loading, validation, canonical dataframe construction.
- `baseline/`: trivial baselines and class balance outputs.
- `models/`: model strategies and saved model runs.
- `embeddings/`: text-instance table, embedding cache, and embedding joins.
- `features/`: engineered feature extraction outputs.
- `calibration/`: probability calibration, threshold sweeps, reliability outputs.
- `scaling/`: learning curve runs and summaries.
- `outputs/` or timestamped subfolders under each stage.

This can initially be much lighter than the May implementation. The important part is to keep the data contract, splits, metrics, and artifacts consistent from the beginning.

## Open Design Questions

- What is the canonical content grouping key: post id, pair id, original/flip text hash, or another identifier?
- Should the primary generalization target be unseen content, unseen participants, or both?
- Are participant attributes intended to be predictive features, stratification variables, or only audit fields?
- Is remove the only positive class of interest, or do we also need keep-quality metrics for downstream use?
- Which feature families are worth extracting manually versus using existing classifiers/analysis pipelines?

## Proposed First Milestone

The first milestone should stop before deep implementation:

- validated canonical dataset;
- class balance and duplicate audit;
- agreed split policy;
- Stage 0 baselines;
- one simple Stage 1 model;
- initial metrics report with remove-focused evaluation.

After that milestone, it will be much clearer whether to prioritize embeddings, explainable feature extraction, or scaling curves next.
