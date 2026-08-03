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
| **Control** | Regular keep/remove classification prompt (study-linked-fate style; pinned above) |
| **Treatment** | Classification prompt built from the truncated feature set produced in Part 1 |

Two parts:

1. **Part 1 — Feature selection.** Turn the mined feature/theme pool into a small, deduplicated, topic-artifact-filtered feature set.
2. **Part 2 — Prompt comparison.** Run both arms on the same 500-post subset and compare agreement with human modal keep/remove labels.

```text
PR #33 stage-1 features (+ stage-2 themes as auxiliary signal)
        │
        ▼
Part 1: extract → pool (+ metadata) → cluster → dedupe → filter topic artifacts
        │
        ▼
truncated feature checklist
        │
        ▼
Part 2: 500 posts → batches of 5 → Control prompt vs Feature prompt → compare to human labels
```

---

## Part 1: Figure out which features we want to use

Inspired by the three-step pipeline in [docwriter-org/mine-writing-rules](https://github.com/docwriter-org/mine-writing-rules/blob/main/README.md):

> First, an extraction step read each guide and pulled out its concrete style rules. This produced the pool in `data/pool.json`.
>
> Second, a clustering step read the whole pool and built the categories up from the rules themselves, rather than starting from a fixed list. It then assigned every rule to one category.
>
> Third, a dedupe step went category by category and merged rules that said the same thing, joining their source lists into one.

We already have the upstream “mining” from PR #33. Part 1 reuses those outputs as the raw pool and runs extract → cluster → dedupe (plus a topic-artifact filter) to produce a truncated feature set suitable for a classification prompt.

### Step 1 — Extract into a base pool (with metadata)

Flatten stage-1 feature records (and optionally stage-2 theme rows as secondary sources) into a single pool, analogous to `data/pool.json` in mine-writing-rules.

Each pool item should carry enough metadata to support clustering, filtering, and audit:

| Field | Purpose |
| ----- | ------- |
| `id` | Stable pool id |
| `feature_text` / `feature_name` + `feature_value` | Concrete feature statement |
| `category` | Stage-1 category tag if present (`surface_lexical`, `topic_subject`, …, `open_ended`) |
| `label_affinity` | `keep`, `remove`, or both (from which side it was extracted / theme keep-vs-remove counts) |
| `source_batch_ids` / `source_message_ids` | Provenance |
| `evidence_span` / `rationale` | Audit trail |
| `is_topic_domain` | Provisional flag for policy-topic features (guns, abortion, …) — see filter below |
| `source_stage` | `stage1_feature` vs `stage2_theme` |

Output: a pool JSON (e.g. `data/pool.json` under a new experiment folder) that is the only input to clustering.

### Step 2 — Cluster and build categories from the features

Do **not** start from a fixed taxonomy. Let categories emerge from the pool itself (same philosophy as mine-writing-rules `workflows/cluster.js`).

Clustering options to investigate (pick one after a small bake-off; document the choice):

1. **Embedding + K-means** — embed `feature_text`, choose \(k\) via silhouette / elbow, assign each feature to a cluster; name clusters with a short LLM pass over cluster members.
2. **Hierarchical clustering + dendrogram** — agglomerative clustering on the same embeddings; cut the tree at a height that yields a readable number of categories; inspect the dendrogram before freezing the cut.
3. **LLM-assisted clustering (mine-writing-rules style)** — shard the pool, ask an LLM to propose categories from the rules and assign each rule; useful as a qualitative check against the geometric methods.

Deliverables from this step:

- `data/taxonomy.json` — emergent categories with short definitions
- `data/assignments.json` — every pool item → one category
- Optional: dendrogram / cluster diagnostics figure for the review writeup

### Step 3 — Dedupe within categories

Category by category, merge features that say the same thing (near-duplicate wording or same operational cue). Join provenance lists (`source_batch_ids`, keep/remove counts) onto the survivor.

Output: a merged feature list (analogous to `writing-rules.json`) — still pre-filter.

### Topic-artifact filter (required)

**Filter out rules whose substance is “this post is about guns / abortion / …”** (and similarly immigration, climate, elections *as topic tags*). Those are artifacts of how we ingested data: we intentionally queried for keywords including `"guns"` and `"abortion"`, among others. Topic presence is not a stance-neutral signal of justified disagreement; the discovery run’s own interpretation already notes that tone/form dominates topic.

Keep features that are **form / rhetoric / pragmatics** even when the example text happens to be about guns or abortion (e.g. “profanity + us-vs-them”, “conspiratorial framing”, “call to violence”). Drop features whose *definition* is the policy domain itself (e.g. theme rows like “Gun rights / gun reform policy advocacy”, “Policy domain focus: abortion/reproductive rights”).

Apply this filter after dedupe (or as a hard exclusion during extract for obvious `primary_policy_domain` / topic-only items). Record excluded items in an audit file so the cut is reviewable.

### Part 1 exit criteria

A short, human-reviewable **truncated feature checklist** (target: small enough to fit in a classification prompt — order-of-magnitude tens of features, not hundreds), grouped by emergent categories, with:

- No topic-domain artifact features
- Provenance back to the PR #33 pool
- Keep-vs-remove affinity notes where stable

This checklist becomes the only feature content injected into the treatment prompt in Part 2.

---

## Part 2: Compare feature-based prompt vs regular classification prompt

### Dataset

- Source: Study Phase 2 Part 2 results via `shared/data/` (`STUDY_PHASE_2_PART_2_RESULTS_FULL`), modal keep/remove per post (tie → remove), same recipe as PR #33.
- Sample: **500 posts**, stratified by keep/remove, frozen to a CSV with a fixed seed so re-runs do not reshuffle.
- Prefer posts **held out** from the PR #33 50% discovery subset when possible, so Part 2 is not scoring the same posts that minted the features. If full holdout is impractical, document overlap and treat results as exploratory.

### Batching

- Group into **batches of 5 posts** per LLM call (100 batches).
- Batch composition: decide and pin before the run (e.g. mixed keep/remove within each batch vs homogeneous). Mixed is closer to the discovery setup; either is fine as long as both arms see identical batches.

### Experimental design

| Factor | Value |
| ------ | ----- |
| Varied | Prompt only (control vs feature-conditioned) |
| Held fixed | Model, temperature / decoding, post texts, batch membership, seed |
| Labels | Human modal keep/remove |
| Unit of analysis | Per-post predicted label (and optional confidence) |

**Control arm:** pinned regular classification prompt (study-linked-fate template).

**Treatment arm:** same task framing, but the system/user instructions include the Part 1 truncated feature checklist as the criteria to weigh (e.g. “prefer remove when these remove-leaning cues are present; prefer keep when these keep-leaning cues dominate; ignore policy topic alone”). Exact wording is an implementation detail; the scientific constraint is that treatment content is derived only from the Part 1 checklist.

### Metrics (minimal)

- Accuracy / F1 vs human modal label (overall and per class)
- Agreement between control and treatment (where they diverge is as interesting as who wins)
- Optional: calibration of remove probability if the schema asks for it

No need for a large metric suite in v1; the question is whether feature grounding changes decisions in a label-aligned way.

### Outputs

Under a new experiment folder (name TBD at implementation time), write:

- Frozen 500-post subset CSV
- Per-arm per-batch JSON predictions
- A short `RESULTS.md` comparing the two arms

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

1. **Clustering method:** K-means vs hierarchical dendrogram cut vs LLM-assisted (or geometric first, LLM naming second).
2. **Target size of truncated checklist** after dedupe + topic filter (e.g. ~15–40 features).
3. **Control prompt pin:** study-linked-fate `STUDY_PROMPT_TEMPLATE` vs a simpler one-shot original/mirror prompt from `models/llm_api/`.
4. **Holdout:** require zero overlap with the PR #33 50% subset, or allow overlap and flag it.
5. **Batch label mix:** mixed keep/remove in each batch of 5 vs random batches.
6. **Model:** stay on `gpt-5.4-nano` for cheap iteration, or match a stronger baseline used in prior keep/remove LLM runs.

---

## Suggested next steps after this draft is approved

1. Implement Part 1 as a small experiment/script package that reads PR #33 outputs → writes pool / taxonomy / assignments / truncated checklist.
2. Human review of the truncated checklist (especially the topic-artifact cut).
3. Implement Part 2 runner (500 posts, batches of 5, two prompt arms).
4. Write `RESULTS.md` and decide whether feature-conditioned prompting is worth scaling or folding into a trained model.
