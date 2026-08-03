# Prompt engineering with LLM feature clusters

**Date:** 2026-08-02  
**Status:** Plan only — no implementation yet  
**Upstream feature curation:** `experiments/create_llm_feature_clusters_2026_08_02/`  
**Strategy context:** `strategy_planning/prompt_experimentation_2026_08_01.md`

---

## Goal

Compare two keep/remove classification prompts on the same posts. **Vary only the prompt.** Same posts, same batching, same model, same decoding.

| Arm | Prompt |
| --- | ------ |
| **A (control)** | Regular study-linked-fate classification prompt |
| **B (treatment)** | Same task framing + the combined keep/remove criteria lists from feature clustering |

Score both arms against human modal keep/remove labels. Also inspect where the arms disagree.

---

## Upstream inputs (Arm B features)

Arm B’s feature checklist is the **union** of the final criteria lists produced by:

| Class | Source |
| ----- | ------ |
| Keep criteria | `experiments/create_llm_feature_clusters_2026_08_02/keep/part_3/` (final checklist) |
| Remove criteria | `experiments/create_llm_feature_clusters_2026_08_02/remove/part_3/` (final checklist) |

Do not re-mine features in this experiment. Wait for those Part 3 outputs (or pin explicit paths once they exist). If multiple clustering methods produced final lists, pin which method’s lists Arm B uses before the run.

---

## Control prompt (Arm A)

Pin the study-linked-fate style prompt used in the keep/remove LLM baselines:

- `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py` — `STUDY_PROMPT_TEMPLATE`

(Related one-/few-shot variants under `experiments/predict_keep_remove_2026_07_01/models/llm_api/` are siblings; this experiment holds one control prompt fixed.)

---

## Dataset

- Source: Study Phase 2 Part 2 results via `shared/data/` (`STUDY_PHASE_2_PART_2_RESULTS_FULL`).
- Labels: modal keep/remove per post (tie → remove), same recipe as PR #33 / the feature-generation experiment.
- Sample: **500 posts**, stratified by keep/remove, frozen to a CSV with a fixed seed.
- Prefer posts **held out** from the PR #33 50% discovery subset when possible so this comparison is not scoring the same posts that minted the features. Document overlap if full holdout is impractical.

---

## Batching and run shape

- Group into **batches of 5 posts** (100 batches).
- Both arms see **identical** batches.
- Pin batch composition before the run (mixed keep/remove vs random); mixed is closer to the discovery setup.

```text
500 posts (frozen)
  → batches of 5
  → Arm A: regular study prompt
  → Arm B: study task + combined keep/remove criteria checklist
  → compare predictions to human modal labels
  → analyze A↔B disagreements
```

---

## Treatment prompt (Arm B)

Same allow/remove task as Arm A, but the instructions include the combined keep + remove criteria checklist as the cues to weigh (e.g. prefer remove when remove-leaning cues dominate; prefer keep when keep-leaning cues dominate; ignore policy topic alone). Exact wording is an implementation detail; scientific constraint: treatment content is derived only from the upstream Part 3 checklists.

---

## Metrics

- Accuracy / F1 vs human modal label (overall and per class), per arm
- Agreement between Arm A and Arm B
- Qualitative / tabulated look at **disagreement cases** (A keep / B remove and vice versa) — as important as which arm wins

Optional: calibration of remove probability if the response schema asks for it.

---

## Outputs

Under this experiment folder:

- Frozen 500-post subset CSV
- Per-arm per-batch JSON predictions
- `RESULTS.md` comparing Arm A vs Arm B (including disagreement analysis)

---

## Dependencies / order

1. Finish `experiments/create_llm_feature_clusters_2026_08_02/` through Part 3 for both `keep/` and `remove/`.
2. Pin which clustering method’s final lists Arm B uses.
3. Implement and run this experiment.

---

## Open decisions

1. Model id (cheap iteration vs match prior keep/remove LLM baselines).
2. Strict holdout from the PR #33 50% subset vs allow overlap.
3. Batch label mix (mixed vs random).
4. Which Part 3 method (k-means vs hierarchical) supplies Arm B’s checklist if both are retained.
