# Predict Phase 2 Part 3 keep or remove decisions with Jev and GEPA

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Delegated tasks must be impossible to misread.

## Overview

We will predict per-post keep or remove labels from the Phase 2 Part 3 linked-fate study. Jev is the baseline scorer, and Jev plus GEPA is the optimizer. The experiment folder is `experiments/predict_keep_remove_jev_gepa_2026_09_23/`. Artifacts upload to `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/`. Tracking uses the Wandb project [predict_keep_remove_jev_gepa_2026_09_23](https://wandb.ai/mind_technology_lab/predict_keep_remove_jev_gepa_2026_09_23).

On 2026-09-24 we confirmed AWS STS, S3 list, Wandb auth, Jev probe calls (9 batch-10 requests, 30 posts, seed 20260924), and OpenAI credentials for GEPA reflection. Data comes from the Phase 2 Part 3 results export (131,175 rows) and stimuli file (18,899 posts). After deduplication and filtering to scored moderation trials, cohort A has 14,941 posts with majority labels and at least three raters (ties dropped). Cohort B is the unanimous subset (4,889 posts).

**Gate:** user approval of this plan before Step 1. After approval, run Stage A Jev baselines first, then Stage B GEPA without a separate review gate between stages.

Stage A scores four Jev prompt arms on all of cohort A. Stage B runs four GEPA optimizations plus transfer evaluations. Analysis clusters errors and mines GEPA prompt criteria against human-mined criteria. Layout and technical detail are in [design.md](./design.md). Cost and time tables are in [estimates.md](./estimates.md).

## Key questions

1. How well does Jev with the exact study stimulus predict majority keep or remove, versus trivial baselines?
2. How much does GEPA improve on that seed on held-out test data, and at what cost?
3. Which text carries the signal: pair view versus original only versus mirror only? Do single-text arms agree for the same pair?
4. Do errors concentrate by stance or toxicity?
5. Does Jev probability of remove track human disagreement and remove-vote share?
6. Do GEPA prompts transfer across text views?
7. What criteria did GEPA discover, and how do they compare with human-mined criteria?
8. What are latency p50, p90, and p99 per request and per post at batch size 10?

## Ablations

| ID | Stage | View | Prompt / reward | Notes |
|----|-------|------|-----------------|-------|
| A1 | Jev baseline | Pair | Study instruction | Primary baseline |
| A2 | Jev baseline | Original only | Study instruction (single-post edit) | |
| A3 | Jev baseline | Mirror only | Study instruction (single-post edit) | |
| A4 | Jev baseline | Pair | Study instruction + human-mined criteria addendum | Feature-injection ablation |
| B1 | Jev + GEPA | Pair | GEPA on A1 seed | Primary GEPA run |
| B2 | Jev + GEPA | Original only | GEPA on A2 seed | |
| B3 | Jev + GEPA | Mirror only | GEPA on A3 seed | |
| B4 | Jev + GEPA | Pair | GEPA on A1 seed with asymmetric reward from issue #299 | TP +1, FN -3, FP -1, TN +0.5 |
| Transfer | Eval only | Cross-view | B1 prompt on original and mirror; B2 on mirror; B3 on original | No new optimization |

Post-hoc on A1 through A4 (no new Jev calls): dev-tuned threshold and subgroup metrics (stance, toxicity, unanimous versus split posts).

## Estimates

| Stage | Jev cost | Reflection cost | Wall time | Notes |
|-------|----------|-----------------|-----------|-------|
| A (A1 to A4) | ~$0.93 | $0 | ~20 min | Rate cap binds at 1,000 requests/min |
| B (4 runs + transfer) | ~$3.4 | ~$51 to $80 (cap $80) | ~2 to 3 h parallel | Reflection dominates |
| Total | ~$4.3 | ≤ $80 | ~3 h | Project cap ≤ ~$90 |

Re-check after 100-post smoke per view. Full token, latency, and per-ablation breakdown: [estimates.md](./estimates.md).

## Happy flow

An operator approves this plan, scaffolds the experiment folder, builds frozen labels and splits, runs Stage A Jev baselines, then Stage B GEPA optimizations in parallel, and finishes with error clustering and criteria mining. Headline test metrics land in `RESULTS.md` and Wandb; large files go to S3.

```mermaid
flowchart TD
  approve[Plan approved]
  scaffold[Scaffold folder deps S3 Wandb]
  labels[Build cohort A splits upload]
  smoke[100-post smoke per view]
  stageA[Stage A A1 to A4 on cohort A]
  stageB[Stage B B1 to B4 parallel GEPA]
  transfer[Transfer evals on dev and test]
  analysis[Clustering and criteria mining]
  results[RESULTS.md and Wandb artifacts]
  approve --> scaffold
  scaffold --> labels
  labels --> smoke
  smoke --> stageA
  stageA --> stageB
  stageB --> transfer
  transfer --> analysis
  analysis --> results
```

## Approach

We reuse the batched Jev scorer pattern from the speedup experiment (batch 10, 1,000 requests per minute, resume, deadletter, latency logging) and the study-faithful prompt from the reasoning-during-moderation experiment. GEPA optimizes the per-post instruction text while post content stays in scorer state, so the seed matches what participants saw. The dev set selects the final GEPA candidate by F1 at threshold 0.5, and we touch the test set once for reporting.

## Steps

### Step 1: Scaffold the experiment folder, dependencies, and tracking

Create `experiments/predict_keep_remove_jev_gepa_2026_09_23/` with README, SETUP, and RESULTS stubs. Add Jev SDK and GEPA optimizer dependencies to `pyproject.toml`. Port S3 and Wandb helpers from the reasoning-during-moderation experiment shared folder.

### Step 2: Build labels and frozen splits from the Phase 2 Part 3 export

Dedupe to one rating per participant and post, aggregate majority labels with at least three raters (ties dropped), and build the unanimous subset. Stratify splits by label, stance, and toxicity (seed 20260924). Upload the frozen parquet to S3 and log as a Wandb artifact. Cover with unit tests.

### Step 3: Build study-faithful prompt rendering for pair, original, and mirror views

Copy study instruction text from the reasoning-during-moderation shared prompt file. Render Post 1 and Post 2 with deterministic hash order. Document and test the single-post instruction diff for original-only and mirror-only arms.

### Step 4: Port the batched Jev scorer and run 100-post smoke per view

Port batching, rate limiter, retries, deadletter, resume, latency, and pricing modules into shared. Unit-test the scorer with a stand-in API client. Run 100-post smoke per view and refresh cost estimates before full Stage A.

### Step 5: Run Stage A (A1 to A4) on cohort A

Score all 14,941 posts per ablation. Compute F1, accuracy, precision, recall, balanced accuracy, ROC-AUC, PR-AUC, trivial baselines, subgroup metrics, and Spearman correlation with remove-vote share. Log to Wandb and upload to S3. Write Stage A tables in `RESULTS.md`.

### Step 6: Build the GEPA adapter and optimize runner

Implement the GEPA adapter and optimization runner (see design.md for interface detail). Wire reflection model, candidate selection on dev F1, and Wandb logging. Unit-test scoring, feedback fields, and budget caps. Run a tiny-budget smoke.

### Step 7: Run Stage B (B1 to B4 plus transfer evals)

Run four GEPA processes in parallel (250 requests per minute each). Pick final prompts on dev. Report test once per ablation. Log candidates, per-iteration valset scores, and artifacts. Write Stage B tables in `RESULTS.md`.

### Step 8: Analysis

Cluster test-set errors from A1 and B1 (K-means baseline, then BERTopic; original and mirror separately). Mine GEPA final prompts into atomic criteria and compare with human-mined criteria. Answer the key questions in `RESULTS.md`.

## What "done" looks like

1. `experiments/predict_keep_remove_jev_gepa_2026_09_23/` has README, SETUP, RESULTS, shared modules with tests, `jev_baseline/`, `jev_gepa/`, and `analysis/` folders.
2. Frozen cohort A splits parquet is on S3 and in Wandb artifacts (test 20%, dev 10%, GEPA pool 70% with balanced train and val subsets).
3. Stage A A1 through A4 `results.json`, `labels.parquet`, and Wandb runs exist under `jev_baseline/` with headline test metrics and latency percentiles.
4. Stage B B1 through B4 GEPA run dirs, final prompts, dev-selected candidates, and single test read exist under `jev_gepa/` with transfer eval results.
5. `RESULTS.md` reports Stage A and B tables, subgroup metrics, trivial baselines, correlation with remove-vote share, clustering summary, and criteria comparison.
6. Shared unit tests pass (exact command in design.md).
7. Total spend stays within the ~$90 project estimate after smoke re-check.

## Decisions for you

1. **Reflection model:** OpenAI gpt-5.4 for the reflection step only (recommended) versus Qwen3.5 4B on Hugging Face Jobs.
2. **Primary cohort:** majority with at least three raters, ties dropped (recommended) versus unanimous-only.
3. **GEPA budget:** 9,000 metric calls and $20 reflection cap per run (recommended as stated).
4. **A4 and B4 ablations:** include human-mined criteria injection and asymmetric reward runs, or drop one or both to save cost.
