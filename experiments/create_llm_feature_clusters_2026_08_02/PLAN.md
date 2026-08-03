# Create LLM feature clusters (keep vs remove)

**Date:** 2026-08-02  
**Status:** Plan only — no implementation yet  
**Upstream discovery:** [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33) — `experiments/llm_based_feature_generation_2026_07_31/`  
**Downstream consumer:** `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/`  
**Strategy context:** `strategy_planning/prompt_experimentation_2026_08_01.md`

---

## Goal

Turn the mined keep/remove features from PR #33 into two truncated, deduplicated **criteria lists** — one predictive of **keep**, one predictive of **remove** — by running the same three-part pipeline independently on each label class.

The combined keep + remove criteria lists feed the Arm B prompt in `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/`.

---

## Layout

```text
experiments/create_llm_feature_clusters_2026_08_02/
  PLAN.md
  keep/
    part_1/   # Extract features into a pool (+ metadata)
    part_2/   # Cluster (k-means + hierarchical) → label clusters via LLM
    part_3/   # Dedupe → final keep criteria list
  remove/
    part_1/
    part_2/
    part_3/
```

`keep/` and `remove/` are parallel runs of the same three parts. Logic should be shared where possible (same scripts, different input label / output roots); do not fork divergent pipelines per class.

---

## Inputs

| Source | Path |
| ------ | ---- |
| Stage-1 feature batches | `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-13:41:56.547131/` |
| Stage-2 themes (optional auxiliary) | `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/` |
| Writeup | `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` |

Split the stage-1 pool by label affinity:

- **keep pipeline** → features extracted from keep-labeled posts (`keep_features` in stage-1 JSON)
- **remove pipeline** → features extracted from remove-labeled posts (`remove_features` in stage-1 JSON)

---

## Part 1 — Extract into a base pool

**Folder:** `{keep,remove}/part_1/`

Flatten the label-specific stage-1 feature records into a single pool JSON, with metadata tagging.

Each pool item should include at least:

| Field | Purpose |
| ----- | ------- |
| `id` | Stable pool id |
| `feature_text` / `feature_name` + `feature_value` | Concrete feature statement |
| `category` | Stage-1 category tag if present (`surface_lexical`, `topic_subject`, …, `open_ended`) |
| `label_affinity` | `keep` or `remove` (fixed for that pipeline) |
| `source_batch_ids` / `source_message_ids` | Provenance |
| `evidence_span` / `rationale` | Audit trail |
| `is_topic_domain` | Provisional flag for policy-topic features (guns, abortion, …) |

**Topic-artifact filter (apply here or as a hard exclusion before clustering):** drop items whose substance is “this post is about guns / abortion / …” (and similar domain tags). Those are artifacts of keyword ingestion, not stance-neutral moderation form. Keep form/rhetoric features even when the evidence text happens to mention those topics. Write excluded items to an audit file.

**Output:** `{keep,remove}/part_1/outputs/pool.json` (path exact TBD at implementation; one pool per label class).

---

## Part 2 — Clustering + creating category labels

**Folder:** `{keep,remove}/part_2/`

Do **not** start from a fixed taxonomy. Build categories from the features themselves.

### 2a — Generate clusters (both methods)

Run **both** clustering methods on the same Part 1 pool embeddings:

1. **K-means** — choose \(k\) via silhouette / elbow (document the choice); assign every feature to a cluster.
2. **Hierarchical clustering + dendrogram** — agglomerative clustering on the same embeddings; cut the tree at a readable height; save the dendrogram as an asset for review.

Each method writes a **`categories.json`** in the **same schema** (so downstream labeling does not care which method produced the file). Store cluster assets under method-specific directories, e.g.:

```text
{keep,remove}/part_2/outputs/
  kmeans/
    categories.json
    …cluster diagnostics…
  hierarchical/
    categories.json
    dendrogram.(png|svg|pdf)
    …cluster diagnostics…
```

**Required `categories.json` shape (both methods):**

```json
{
  "method": "kmeans" | "hierarchical",
  "label_affinity": "keep" | "remove",
  "clusters": [
    {
      "cluster_id": "0",
      "member_feature_ids": ["…"],
      "member_features": [
        {
          "id": "…",
          "feature_text": "…"
        }
      ]
    }
  ]
}
```

Exact field names can be tightened at implementation time; the hard constraint is that **k-means and hierarchical emit the same file format**.

### 2b — Label clusters with an LLM

Separate script (shared across keep/remove and across methods):

`generate_categories_for_clusters.py`

- **Input:** path to a `categories.json` (works for either method).
- **Context:** pass the clusters plus the problem framing (linked-fate keep/remove moderation; we want category labels that capture linguistic/rhetorical form predictive of this label class).
- **Output:** each cluster gets a short human-readable **category label** (and optional one-line definition). Write alongside the input, e.g. `categories_labeled.json`, without mutating the unlabeled asset.

Flow:

```text
pool.json
  → embed
  → k-means          → kmeans/categories.json       → generate_categories_for_clusters.py → labeled
  → hierarchical     → hierarchical/categories.json → generate_categories_for_clusters.py → labeled
```

---

## Part 3 — Deduplicate and create the final criteria list

**Folder:** `{keep,remove}/part_3/`

For each labeled clustering method (or for a chosen primary method after review):

1. Within each category, merge features that say the same thing (near-duplicate wording / same operational cue).
2. Join provenance onto survivors.
3. Emit a truncated **final criteria list** for that label class — small enough to inject into a classification prompt.

**Outputs (per label class):**

- Deduped category → feature map
- Final criteria checklist for keep (under `keep/part_3/`) and for remove (under `remove/part_3/`)

These two checklists are what `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/` combines for Arm B.

---

## What “done” looks like for this experiment

1. `keep/` and `remove/` each have runnable part_1 → part_2 → part_3 (or documented CLI entry points).
2. Part 2 produces `categories.json` for **both** k-means and hierarchical, same schema.
3. `generate_categories_for_clusters.py` labels either method’s `categories.json` without method-specific branches beyond reading the shared schema.
4. Part 3 emits a final keep criteria list and a final remove criteria list, with topic-domain artifacts filtered out.
5. Assets (pools, clusters, dendrograms, labeled categories, final lists) are written under the experiment tree and are auditable.

---

## Open decisions

1. Embedding model for clustering.
2. How \(k\) / dendrogram cut is chosen and whether both methods’ labeled outputs are kept through Part 3 or one is selected after review.
3. Whether stage-2 themes are merged into the Part 1 pool or ignored.
4. Target size of each final criteria list.
