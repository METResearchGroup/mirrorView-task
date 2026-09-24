# Generate LLM features for Phase 2, Part 3 linked-fate moderation data

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Delegated tasks must be impossible to misread.

## Overview

The goal is a new experiment at `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/` that discovers, normalizes, and operationalizes moderation features on the 18,899 Phase 2, Part 3 posts. The pipeline runs separately on original text, mirrored text, and paired original plus mirror text. It follows the lab Discover, Normalize, Operationalize method in [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md) and [HOW_TO_CLUSTER_TEXT.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_CLUSTER_TEXT.md). Copy and adapt Part 2 reference code from `experiments/create_llm_features_2026_08_05/src/` (`llm_generate_features.py`, `generate_embeddings.py`, `cluster_embeddings.py`, `generate_labels_for_embeddings.py`, `prompts.py`, `schemas.py`, `paths.py`), and copy mixed-batch prompt patterns from `experiments/llm_based_feature_generation_2026_07_31/prompts.py`, `schemas.py`, and `stage1.py`. Do not add cross-experiment imports. Upload artifacts to `s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/` with the same prefix as the local folder.

A 50/50 post-level discovery versus held-out split prevents double dipping. Stratify the split by modal keep/remove label, sampled stance, toxicity bucket, and Part 2 catalog overlap. Run feature mining only on discovery posts, and reserve the held-out half as the test set for every Q1 through Q7 analysis. After you approve the codebook, label all 18,899 posts with original and mirrored text coded separately. Use discovery-half labels only for description, Part 2 overlap description on all 8,899 shared posts, and downstream reuse. Run every hypothesis test and model comparison for Q1 through Q7 on the held-out half only. Commit the post-ID lists to fix the Part 2 reproducibility gap, because the sampled subset CSV was never committed.

Part 2 (`experiments/llm_based_feature_generation_2026_07_31/`, `experiments/create_llm_features_2026_08_05/`) used mixed-contrast batches (10 keep plus 10 remove) and a two-stage theme synthesis that produced 132 themes. Per `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`, rhetorical form (profanity, dehumanization, ridicule, us-vs-them, conspiracy) predicted remove better than policy topic, while argument and evidence predicted keep. Because Part 2 passed original and mirror jointly with no separate arms, Part 3 adds the three-arm comparison that Part 2 could not run.

Phase 2, Part 3 (`shared/data/raw/study_phase_2_part_3/`, `docs/runbooks/HISTORY_OF_STUDY.md`) finished data collection in September 2026. Its catalog has 18,899 posts, including 8,899 shared with the Part 2 June catalog and 10,000 new in Phase 2, Part 3. The export has 3,875 finishers, 79,500 scored linked-fate labels, a ~69.6% keep rate, and linked-fate decisions that cover both texts in a pair.

## Happy flow

An engineer builds the post-level cohort and a reproducible two-way split (discovery and held-out test), runs naive baselines and the three-arm LLM discovery pipeline on the discovery half, merges per-arm clusters into a human-approved codebook, labels all 18,899 posts with original and mirror coded separately, runs a self-consistency check on a 200-text sample, and writes `RESULTS.md` with tables that answer the seven research questions on the held-out half only.

```mermaid
flowchart LR
  A[Load Phase 2, Part 3 data] --> B[Build cohort and two-way split]
  B --> C[Naive baselines per text arm]
  B --> D[LLM feature discovery per arm]
  D --> E[Embed and cluster features]
  E --> F[Merge into shared codebook]
  F --> G[User approves draft codebook]
  G --> H[Label all posts]
  H --> I[Self-consistency check on 200 texts]
  I --> J[Analyze held-out test set and write RESULTS.md]
  C --> J
```

## Approach

Run naive baselines first. Compute document-frequency unigrams and bigrams by keep versus remove, and run K-Means on Titan post embeddings with a k sweep. Then run the LLM batch feature generation pipeline with mixed-contrast batches as the primary design and single-class batches as an ablation.

Embed generated features with Titan (`shared/embeddings/bedrock.py`), cluster with HDBSCAN as the primary method and K-Means as a comparison, and name clusters with an LLM. Run three random seeds and report cluster stability within and across text arms. Merge per-arm clusters into one shared codebook. By default, do not merge features. Merge two features only after side-by-side review of example posts and a human confirms the match. Record confirmed merges in a committed synonym list file under the experiment folder, and present the draft codebook for human review before labeling starts.

Use `gpt-6-luna` (API model id `gpt-6-luna`) for every LLM step: feature generation, cluster naming, codebook merge support, Part 2 theme mapping support, and labeling. Set reasoning effort to none on every call, because GPT-6 Luna defaults to medium and you must record the setting in run metadata. Part 2 used `gpt-5.4-nano`, so Part 2 versus Part 3 theme differences mix a model change with a data change, and the Q1 replication result must state that. Smoke test one batch per text arm before any production run. The smoke test must confirm that LiteLLM directly (model `openai/gpt-6-luna`) accepts the model id and the no-reasoning setting, and that run metadata shows zero reasoning tokens. Do not start production until the user approves. Do not run a model ablation; keep the model fixed.

## Steps

### Step 1: Build post-level cohort and discovery and held-out split

Aggregate Phase 2, Part 3 moderation trials from `shared/data/raw/study_phase_2_part_3/results/full.csv` joined to `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv`. Label counts per post vary widely: 1,145 posts have 1 label, 1,755 have 2, and 15,966 have 3 or more (moderation-trial rows with phase equal to 1). Use modal keep/remove as the primary label and the stratification label for every post. Apply three-group labels (unanimous keep, split, unanimous remove) only to eligible posts, following the logic in `experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py`. After you drop conflicting worker-post pairs and deduplicate to one row per worker per post, a post must have at least 4 raters to receive a three-group label. Split posts have a two-two, three-two, or two-three keep-remove vote split. Unanimous keep posts have only keep votes and at least 4 raters. Unanimous remove posts have only remove votes and at least 4 raters. Posts with fewer than 4 raters or any other vote pattern receive no three-group label. Apply a 50/50 discovery versus held-out split stratified by modal keep/remove label, sampled stance (left or right), sampling toxicity bucket (low, middle, or high), and whether the post appears in the Part 2 June catalog (8,899 of 18,899). Reserve the held-out half as the test set for all Q1 through Q7 analyses. Upload the split to S3 and commit the post-ID lists under `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/`. Run the attention-check filter as an ablation: all participants versus attention-check passers only (77.2% pass rate in the Phase 2, Part 3 export).

### Step 2: Naive baselines per text arm

On discovery posts only, compute document-frequency unigrams and bigrams separately for keep versus remove (not TF-IDF) in each text arm (original only, mirror only, paired). Embed posts with Titan and run K-Means with a k sweep (2 through 10) as a clustering baseline before any LLM-generated features. Store outputs under `outputs/original_only/baselines/`, `outputs/mirror_only/baselines/`, and `outputs/paired/baselines/`, and upload them to S3.

### Step 3: LLM batch feature generation (discovery half only)

Copy and adapt the reference files listed in the Overview into the new experiment `src/` folder. In each text arm, run mixed-contrast batches (10 keep plus 10 remove) as the primary design, with single-class batches (500 keep, 500 remove, per `experiments/create_llm_features_2026_08_05/README.md`) as an ablation. Use `gpt-6-luna` with reasoning effort set to none on every call, and record the setting in run metadata. Cap at 8 keep plus 8 remove features per batch with evidence spans, matching Part 2 stage 1. Run one smoke batch per arm, and start production only after user approval.

### Step 4: Normalize features (embed, cluster, name)

Embed all generated feature texts with Titan (`shared/embeddings/bedrock.py`, 256 dimensions, L2-normalized). Cluster with HDBSCAN as the primary method and K-Means as a comparison. Ask `gpt-6-luna` (reasoning effort none) to name each cluster from a random sample of member features. Run three random seeds and report cluster overlap across seeds and across text arms. Store outputs under `outputs/original_only/normalize/`, `outputs/mirror_only/normalize/`, and `outputs/paired/normalize/` (each with a run timestamp subfolder).

### Step 5: Operationalize into a shared codebook

Merge per-arm cluster outputs into one shared codebook. Give each entry a short name, one-sentence definition, positive and negative examples, and the text arm where it was discovered. By default, do not merge features. Merge two features only after side-by-side review of example posts and a human confirms the match. Record every confirmed merge in a committed synonym list file under the experiment folder. Present the draft codebook for human review, and do not start labeling until the user approves.

### Step 6: Label all posts and run self-consistency check

Use the approved codebook to have `gpt-6-luna` (reasoning effort none) code every post's original text and mirrored text separately as present or absent per feature. Label all 18,899 posts (37,798 labeling calls). Use discovery-half labels only for description, Part 2 overlap description on all 8,899 shared posts, and downstream reuse. After labeling, re-label a random 200 texts a second time with the same model and settings. Report per-feature self-consistency (share of matching present/absent labels). Flag features below 90% self-consistency in `RESULTS.md`, and do not drop them from analysis.

### Step 7: Analyze and report

On held-out test-set posts only, answer the seven research questions below. To compare Phase 2, Part 3 features to Part 2 themes (`experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`), map each Phase 2, Part 3 codebook feature to the rank-1 nearest Part 2 theme from the two-stage theme synthesis in `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/` using Titan cosine similarity on name plus definition (report the similarity score for each match; no human confirmation step). Report which Part 2 themes replicate on the 8,899 overlapping posts, which Phase 2, Part 3 features are new, and which Part 2 themes disappear. In `RESULTS.md`, state that the mapping is provisional and list the similarity score for each match. In the Q1 replication result, state that Part 2 used `gpt-5.4-nano` while Part 3 used `gpt-6-luna`, so theme differences mix a model change with a data change. Write `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/RESULTS.md` with summary tables, and upload all artifacts to `s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/`.

## Key research questions

| Question | How answered | Text arms used |
| --- | --- | --- |
| Q1: What features separate keep versus remove in Phase 2, Part 3, and do Part 2 themes replicate (including on the 8,899 posts shared with Part 2)? | Build the codebook on the discovery half. Compute feature prevalence and keep-versus-remove tests on the test set only. Map each Phase 2, Part 3 codebook feature to the rank-1 nearest Part 2 theme (Titan cosine similarity on name plus definition; score reported; mapping provisional, no human confirmation) and measure overlap on the shared post subset. State that Part 2 used `gpt-5.4-nano` and Part 3 used `gpt-6-luna`, so replication findings mix model and data changes | All three arms; paired arm for direct Part 2 replication |
| Q2: Which features are stance-invariant (present in both original and mirror) versus stance-specific (appear in only one side)? | Cross-tabulate per-post original versus mirror present/absent labels on test-set posts; classify features by concordance rate | Original only and mirror only (compare labeling outputs per post) |
| Q3: Does the mirror preserve the original's features (flip fidelity)? Report per-feature mismatch rates | Per feature, compute rate where original is present and mirror is absent (and vice versa) on test-set posts | Original only plus mirror only (paired comparison per post) |
| Q4: Which text's features best predict the linked-fate decision: original-only, mirror-only, or both (plus the difference)? | Fit logistic regression models on feature vectors on the test set; compare AUC and log loss across arms and a combined model | Original only, mirror only, paired (and derived difference features) |
| Q5: Do features explain disagreement (split versus unanimous posts)? | Compare feature prevalence across three-group labels (unanimous keep, split, unanimous remove) on eligible test-set posts only; report N per group | All three arms |
| Q6: Do Democrat and Republican moderators remove on different features, conditional on post stance? | Three-way interaction tables: moderator party x post stance x feature presence on remove-labeled trials | All three arms (trial-level rows from the session export) |
| Q7: Do features add predictive value beyond the sampling toxicity bucket and stance? | Nested logistic models with and without toxicity and stance covariates; compare AUC delta on test-set posts | All three arms |

## What is not answerable

- **Causal effects of features.** All analyses are observational. Feature presence correlates with decisions but does not establish causation.
- **Attitude change or persuasion.** Phase 2, Part 3 does not measure whether moderation changed participant attitudes beyond the collected survey fields.
- **Per-text decisions.** Linked-fate means one keep/remove decision covers both original and mirror. You cannot infer separate moderation intent for each text, only separate feature presence.
- **Human-verified labels.** Without human validation, LLM labels are unverified against human judgment, so treat all feature findings as provisional. Human validation is deferred and can be added later without re-running the pipeline.

## Ablation axes

`gpt-6-luna` with reasoning effort none is fixed for all LLM steps. Do not run a model ablation.

| Axis | Values | Primary | Purpose |
| --- | --- | --- | --- |
| Text arm | original only, mirror only, paired original plus mirror | paired (Part 2 replication) | Which text surface drives feature discovery and prediction |
| Batch design | mixed-contrast (10 keep plus 10 remove), single-class (500 per label) | mixed-contrast | Contrastive signal versus class-homogeneous batches |
| Label definition | modal keep/remove (primary and stratification), unanimous-only subset (sensitivity), three-group unanimous keep / split / unanimous remove on eligible posts only (sensitivity; Q5 on eligible test-set posts with N per group) | modal keep/remove for discovery and primary analyses | Sensitivity of features to label strictness |
| Participant filter | all participants, attention-check passers only | attention-check passers | Data quality versus sample size |
| Clustering | document-frequency unigram/bigram baseline, K-Means on post embeddings, HDBSCAN on feature embeddings | HDBSCAN on feature embeddings | Compare simple baselines before trusting LLM clusters |
| Random seeds | 3 seeds | 3 | Cluster stability within and across arms |

## Proposed experiment folder layout

```text
experiments/llm_feature_generation_phase_2_part_3_2026_09_24/
  README.md
  SETUP.md
  RESULTS.md
  src/                          # copied and adapted from create_llm_features_2026_08_05/src/
  data/
    post_split/
      discovery_post_ids.csv    # committed to git
      test_post_ids.csv         # held-out posts for Q1 through Q7
      split_metadata.json
    feature_synonyms.csv        # committed merge decisions
  outputs/
    original_only/
      cohort/
      baselines/
      discovery/
      normalize/
      operationalize/
      analysis/
    mirror_only/
      (same stage folders)
    paired/
      (same stage folders)
    shared/
      codebook/                 # human-approved merged codebook
      label/                    # label shards (labels.jsonl) and label_matrix.parquet
      self_consistency/         # 200-text re-label and per-feature scores
  smoke_tests/
```

S3 mirror: `s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/` (same tree).

## Decisions

1. **Model.** Use `gpt-6-luna` for every LLM step (feature generation, cluster naming, codebook merge support, Part 2 theme mapping support, labeling). Set reasoning effort to none on every call, and record the setting in run metadata. Part 2 used `gpt-5.4-nano`, so Part 2 versus Part 3 theme differences mix a model change with a data change, and the Q1 replication result must state that. The smoke test must confirm that LiteLLM directly (model `openai/gpt-6-luna`) accepts the model id and the no-reasoning setting, and that run metadata shows zero reasoning tokens.
2. **Run timestamps.** All run folders use timestamp format `%Y-%m-%dT%H-%M-%S` (local time).
3. **No human coding for now.** Replace human agreement checks with a self-consistency check. Re-label 200 random texts a second time and flag features below 90% self-consistency in `RESULTS.md`.
4. **Label all posts.** Label all 18,899 posts with original and mirrored text coded separately. Label shards live under `outputs/shared/label/<run_timestamp>/labels.jsonl`, and the assembled matrix is `outputs/shared/label_matrix.parquet`. Use discovery-half labels only for description, Part 2 overlap description, and downstream reuse. Run every hypothesis test and model comparison for Q1 through Q7 on the held-out half only.
5. **Spend cap.** $25 maximum. Stop and report if you exceed it.

## Cost estimate

GPT-6 Luna pricing: $0.10 input / $0.01 cached input / $0.50 output per 1M tokens. No reasoning tokens.

| Item | Estimate |
| --- | --- |
| Labeling calls | 37,798 (18,899 posts x 2 texts), about 3,800 input and 320 output tokens each; codebook (about 95% of input) is identical across calls and cacheable |
| Standard price, no caching | about $22 total |
| With codebook prompt caching | about $10 total |
| With caching plus Batch API (50% off) | about $5 total |
| Discovery, clustering, and naming | about $1.50 of those totals; labeling is the rest |
| Proposed spend cap | $25; stop and report if exceeded |

## What "done" looks like

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/` exists with `README.md`, `SETUP.md`, and `RESULTS.md` per `AGENTS.md` conventions.
- Discovery and test post-ID lists are committed under `data/post_split/` and uploaded to S3.
- Smoke artifacts exist for one batch per text arm and were reviewed before production. Smoke confirms `gpt-6-luna`, reasoning effort none, and zero reasoning tokens in run metadata.
- Naive baselines, LLM discovery outputs, cluster stability reports (3 seeds), and the human-approved shared codebook are on S3 under the experiment prefix.
- All 18,899 posts are labeled (original and mirror separately). Label shards are in `outputs/shared/label/`; `outputs/shared/label_matrix.parquet` is assembled. Self-consistency scores are in `outputs/shared/self_consistency/`; features below 90% are flagged in `RESULTS.md`.
- `RESULTS.md` answers Q1 through Q7 on the held-out test set with tables, documents ablation results, states what is not answerable (including provisional LLM labels), and reports Part 2 replication on the 8,899 shared posts (which Part 2 themes replicate, which Phase 2, Part 3 features are new, which Part 2 themes disappear, and the `gpt-5.4-nano` versus `gpt-6-luna` model change).
- `uv run pytest` passes for any new tests added under the experiment.
