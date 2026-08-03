# Prompt experimentation: feature-conditioned vs regular keep/remove classification

**Date:** 2026-08-01  
**Status:** Draft for review  
**Upstream discovery:** [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33) — `experiments/llm_based_feature_generation_2026_07_31/`  
**Context:** Study Phase 2 Part 2 linked-fate keep/remove labels; see `docs/runbooks/WHAT_IS_MIRRORVIEW.md` and `docs/runbooks/HISTORY_OF_STUDY.md`

---

## Goal

Test whether a classification prompt that is explicitly grounded in a **truncated, curated set of moderation-relevant features** (mined from human keep/remove decisions) outperforms — or meaningfully differs from — our **regular classification prompt** when predicting linked-fate keep/remove labels.

This sits in the Phase 3 research arc: we already have stance-invariant keep/remove labels from the linked-fate procedure; the open question is what linguistic “substance” of justified disagreement those labels encode, and whether making that substance explicit in a prompt improves LLM classification.

---

## Background (what we already have)

PR #33 ran a two-stage LLM pipeline on a frozen 50% Study Phase 2 Part 2 subset:

| Stage | Result |
| ----- | ------ |
| Stage 1 — feature generation | 140 mixed batches (10 keep + 10 remove); **1116** keep features + **1120** remove features |
| Stage 2 — theme synthesis | **132** themes + cross-cutting interpretations |

Artifacts:

- Features: `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-13:41:56.547131/`
- Themes: `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/`
- Writeup: `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`

Cross-cutting signal from that run (high level): moderation outcomes track **rhetorical form** more than policy topic — hostility intensity (profanity, dehumanization, ridicule), us-vs-them framing, conspiracy/disinfo framing, and escalation into punishment/violence lean remove; structured argumentation, empirical/legal support, and non-abusive policy advocacy lean keep. Policy-domain themes (guns, abortion, immigration, etc.) appear in both labels and are often artifacts of how we sampled the corpus.

The **control / regular classification prompt** for comparison is the study-linked-fate style prompt used in the keep/remove LLM baselines — e.g. `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py` (`STUDY_PROMPT_TEMPLATE`: decide allow/remove for a mirrored post pair under a healthy-political-discussion standard). Zero-/one-/few-shot variants under `experiments/predict_keep_remove_2026_07_01/models/llm_api/` are related siblings; the experiment should pin one control prompt and hold it fixed.

---

## Basic approach

Compare two experimental arms. **Vary only the prompt.** Same posts, same batching, same model, same decoding settings.

| Arm | Prompt |
| --- | ------ |
| **A (control)** | Regular keep/remove classification prompt (study-linked-fate style; pinned above) |
| **B (treatment)** | Classification prompt built from the combined keep + remove criteria lists |

Split across two experiment folders:

| Work | Folder | Detail plan |
| ---- | ------ | ----------- |
| Feature curation (extract → cluster → dedupe), run separately for keep and remove | `experiments/create_llm_feature_clusters_2026_08_02/` | `PLAN.md` there |
| Prompt comparison (Arm A vs Arm B on 500 posts) | `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/` | `PLAN.md` there |

```text
PR #33 stage-1 features
        │
        ▼
create_llm_feature_clusters_2026_08_02/
  keep/   part_1 → part_2 → part_3   → keep criteria list
  remove/ part_1 → part_2 → part_3   → remove criteria list
        │
        ▼  combine keep + remove checklists
prompt_engineering_llm_feature_clusters_2026_08_02/
  500 posts → batches of 5 → Arm A vs Arm B → score vs human labels
```

---

## Experiment 1: Create feature clusters (`create_llm_feature_clusters_2026_08_02`)

Full plan: `experiments/create_llm_feature_clusters_2026_08_02/PLAN.md`.

Run the same three-part pipeline independently on **keep** features and **remove** features so we get criteria predictive of each class:

1. **Part 1 — Extract** — flatten label-specific PR #33 features into a pool (+ metadata); filter topic-domain artifacts (guns/abortion/etc. as domain tags).
2. **Part 2 — Cluster + label** — run **both** k-means and hierarchical clustering (+ dendrogram); each method writes the same `categories.json` schema; then `generate_categories_for_clusters.py` asks an LLM for a category label per cluster.
3. **Part 3 — Dedupe** — merge near-duplicates within categories; emit the final criteria list for that label class.

Layout: `keep/{part_1,part_2,part_3}/` and `remove/{part_1,part_2,part_3}/`.

---

## Experiment 2: Prompt comparison (`prompt_engineering_llm_feature_clusters_2026_08_02`)

Full plan: `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/PLAN.md`.

- Freeze **500** posts (modal keep/remove); batches of **5**.
- **Arm A:** regular study-linked-fate prompt.
- **Arm B:** same task + combined keep/remove criteria from Experiment 1 Part 3.
- Metrics: accuracy/F1 vs human labels; agreement between arms; disagreement cases.

Depends on Experiment 1 finishing both `keep/part_3` and `remove/part_3`.

---

## What this is / is not

**Is:**

- A prompt ablation on top of already-mined features from PR #33
- A curation pipeline (extract → cluster → dedupe → topic filter) before any classification run
- A controlled comparison with one varied factor (the prompt)

**Is not:**

- Retraining or fine-tuning a classifier (that can follow if prompts help)
- Re-running the full PR #33 discovery pipeline
- Treating “post is about guns/abortion” as a moderation feature

---

## Open decisions for review

See open decisions in each experiment `PLAN.md`. Cross-cutting ones:

1. Embedding model and how \(k\) / dendrogram cut are chosen.
2. Target size of each final criteria list.
3. Whether Arm B uses k-means lists, hierarchical lists, or a reviewed merge.
4. Holdout from the PR #33 50% discovery subset.
5. Batch label mix and model id for the prompt comparison.

---

## Suggested next steps after this draft is approved

1. Implement `experiments/create_llm_feature_clusters_2026_08_02/` (keep + remove, parts 1–3).
2. Human review of the final keep/remove criteria lists (especially the topic-artifact cut).
3. Implement `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/` and run Arm A vs Arm B.
4. Write that experiment’s `RESULTS.md` and decide whether feature-conditioned prompting is worth scaling.
