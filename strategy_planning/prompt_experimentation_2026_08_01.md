# Prompt experimentation: feature-informed keep/remove classification

**Date:** 2026-08-01  
**Status:** Draft for review  
**Related work:** [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33) (feature generation pipeline, merged), [`experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`](../experiments/llm_based_feature_generation_2026_07_31/RESULTS.md)

---

## 1. Goal

MirrorView's Phase 3 work is about characterizing the **substance of justified disagreement** — the linguistic and rhetorical boundary between posts humans keep vs. remove under linked-fate moderation ([`WHAT_IS_MIRRORVIEW.md`](../docs/runbooks/WHAT_IS_MIRRORVIEW.md)).

PR #33 produced a corpus of LLM-extracted features and synthesized themes from Study Phase 2 Part 2 keep/remove labels. The next step is to test whether **prompting an LLM with those discovered features** improves keep/remove classification vs. the existing study prompt.

**Core comparison:**

| Arm | Prompt |
| --- | --- |
| **Control** | Regular linked-fate classification prompt (`STUDY_PROMPT_TEMPLATE` in `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py`) |
| **Treatment(s)** | Same task framing, but augmented with selected features/themes from the discovery pipeline |

We vary **only the prompt**. Model, temperature, batching, gold labels, and evaluation code stay fixed.

---

## 2. What we have from discovery (PR #33)

### Pipeline recap

```text
Study Phase 2 Part 2 (modal keep/remove per post)
  → Stage 1: per-batch feature extraction (6 fixed categories + open_ended)
  → Stage 2: theme synthesis across batches
```

### Feature categories (maintain this distinction throughout)

| # | Category key | What it captures |
| --- | --- | --- |
| 1 | `surface_lexical` | Register, profanity, punctuation, caps, proper-noun density |
| 2 | `topic_subject` | Policy domain, events, geography, culture-war salience |
| 3 | `semantic_content` | Causal claims, moral language, conspiracy, prescriptions |
| 4 | `pragmatics_intent` | Sarcasm, ridicule, calls to action, outrage, hedging |
| 5 | `target_directionality` | Who is praised/criticized, us-vs-them, mirror shifts |
| 6 | `compositional_syntax` | Conditionals, rhetorical questions, lists, direct address |
| 7 | `open_ended` | Salient features outside the fixed checklists |

### Production outputs (50% subset, frozen)

- **Stage 1:** 140 batches → 1,116 keep features + 1,120 remove features  
- **Stage 2:** 132 synthesized themes with `keep_count` / `remove_count` per theme  
- **Frozen subset:** `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`

### Early signal from themes

Themes skewed toward **remove** (profanity, ridicule, conspiratorial framing, us-vs-them) are strong candidates. Themes that appear in **both** labels (policy advocacy, calls to action, causal claims) are interesting because they suggest *style* matters more than *topic* — matching Phase 2 Part 1 open-ended findings in [`HISTORY_OF_STUDY.md`](../docs/runbooks/HISTORY_OF_STUDY.md).

---

## 3. Open problem: which discovered features should we use?

The discovery corpus is large and redundant (132 themes, thousands of raw features). We need principled ways to **filter, rank, and select** features before putting them in prompts. Below are candidate approaches, grouped by method. **All ranking/selection should happen within category first**, then we combine across categories for broader ablations.

### 3.1 Frequency / prevalence filtering

**Idea:** Within each category, keep the features (or checklist items) that appear most often across stage-1 batches.

| Pros | Cons |
| --- | --- |
| Simple, reproducible, cheap | Common ≠ important; may overweight generic features (e.g., `named_proper_nouns_density`) |
| No extra model calls | Ignores label association |

**Variants:**
- Raw count across all extracted features in a category
- Count weighted by batch (each batch contributes equally)
- Separate top-K for keep-associated vs. remove-associated features

### 3.2 Label-association filtering (keep vs. remove skew)

**Idea:** Rank features by how disproportionately they appear on keep-rated vs. remove-rated posts (or vice versa).

| Metric | Use when |
| --- | --- |
| `remove_rate = n_remove / (n_keep + n_remove)` | Prioritize removal signals |
| `log_odds` or `|keep_rate - base_rate|` | Prioritize features that *discriminate* |
| Theme-level `keep_count` / `remove_count` from stage 2 | Already computed; fast starting point |

**Example from RESULTS.md:** Theme 1 (profanity) has keep=5, remove=20 → strong remove signal. Theme 10 (direct calls to political action) has keep=7, remove=1 → keep-leaning.

### 3.3 Similarity matching and deduplication

**Idea:** Many themes/features are near-duplicates ("Profanity and taboo insults" vs. "Strong profanity, taboo language"). Cluster before selecting.

| Method | Details |
| --- | --- |
| **Embedding clustering** | Embed `feature_name + feature_value + rationale` (or theme `label + defining_features`); cluster within category; pick one representative per cluster |
| **String similarity** | Jaccard / fuzzy match on feature names; merge synonyms (`profanity_or_taboo_language` variants) |
| **Theme merge pass** | Manual or LLM-assisted merge of the 132 themes → ~15–25 canonical themes before prompt insertion |

Keeps prompts short and avoids repeating the same guidance six ways.

### 3.4 Predictive power screening (lightweight supervised)

**Idea:** For each candidate feature, score how well its **presence on a post** predicts modal keep/remove.

1. Reconstruct a post × feature matrix from stage-1 JSON (match `message_id` to labels).
2. Per feature: compute accuracy, precision, recall, F1, or mutual information vs. gold label.
3. Within each category, keep top-K by F1 (or by recall on the minority class).

| Pros | Cons |
| --- | --- |
| Directly optimizes for classification utility | Feature presence is LLM-extracted, not deterministic |
| Complements frequency (rare but predictive features survive) | Needs held-out posts to avoid overfitting to discovery subset |

### 3.5 LLM meta-ranking

**Idea:** Ask an LLM to rank or prune the feature list for **moderation relevance** and **non-redundancy**, given the category and example posts.

**Prompt sketch:** "Given these 40 `pragmatics_intent` features and example keep/remove posts, select the 5–8 features most useful for teaching a moderator what to look for. Prefer features that distinguish keep from remove."

| Pros | Cons |
| --- | --- |
| Can synthesize across batches; handles nuance | Another LLM call; less reproducible unless temperature=0 |
| Good for turning raw features into natural-language prompt bullets | Risk of hallucinating features not in the corpus |

### 3.6 Human expert curation

**Idea:** Researchers review top-N candidates per category (from any automated ranker above) and approve a final shortlist.

Recommended as a **final gate** regardless of automated method — especially for sensitive features (sexual violence references, slurs) where prompt wording matters.

### 3.7 Cross-cutting theme prioritization

**Idea:** Use stage-2 `cross_cutting_themes` (61 listed in RESULTS.md) to identify **feature combinations** that matter, not just singletons.

Examples from production results:
- Hostility intensity stacking: profanity + emphatic formatting + us-vs-them
- Policy advocacy + blame certainty: call_to_action + causal_claim
- Argument structure without abuse: conditionals + evidence → keep-leaning

**Prompt implication:** Some treatment arms should describe **interactions** ("remove when profanity co-occurs with outgroup attack"), not isolated features.

### 3.8 Checklist vs. open-ended prioritization

Within each category, decide whether treatment prompts use:
- **Fixed checklist items** only (from `prompts.py` — auditable, compact)
- **Open-ended discovered features** only (richer, noisier)
- **Checklist + top open-ended** (hybrid)

Recommendation: start with **checklist items** for category ablations (cleaner causal story), then add open-ended features in a later round if checklist-only arms underperform.

---

## 4. Recommended selection workflow (draft)

A practical sequence that combines several methods above:

```text
Per category:
  1. Aggregate stage-1 features → frequency table + keep/remove counts
  2. Cluster / dedupe (embedding or string similarity)
  3. Rank survivors by label-association (log-odds) AND predictive F1 on held-out posts
  4. LLM meta-rank top 15 → shortlist of 5–8 prompt bullets
  5. Human review → final category feature set (target: 3–6 bullets per category)

Cross-category:
  6. Map themes → categories via defining_features
  7. Identify cross-cutting combos for "interaction" treatment arms
```

**Deliverable before running classification experiment:** `data/selected_features_by_category.json` with provenance (which filter step included each feature).

---

## 5. Proposed classification experiment

### 5.1 Sample

| Parameter | Proposed value | Notes |
| --- | --- | --- |
| Posts | **500** | Stratified sample from Part 2 modal labels (balanced keep/remove; optionally stratify by platform, toxicity tier) |
| Gold labels | Modal keep/remove per post | Same derivation as feature-generation pipeline |
| Seed | Fixed (e.g., 42) | Record in metadata |
| Overlap with discovery subset? | **Prefer disjoint** | Discovery used 50% (~4,400 posts). Hold out the 500 from discovery IDs when possible to reduce leakage |

### 5.2 Batching

| Parameter | Proposed value | Rationale |
| --- | --- | --- |
| Batch size | **5 posts** | Smaller than discovery (10+10) because classification is the task, not feature extraction; reduces context dilution |
| Batch composition | Mixed keep/remove within batch | Mirrors discovery setup; prevents position bias |
| Batches | 100 batches × 5 posts = 500 posts | |

**Open question:** Classify **per pair** (one linked-fate decision per post, as in `api_baselines`) or **per batch** (one prompt lists 5 pairs, returns 5 decisions)?

| Mode | Pros | Cons |
| --- | --- | --- |
| **Per pair** (recommended) | Matches existing `IsRemoveResult` schema and prior baselines | 500 calls per arm |
| **Per batch** | Fewer calls (100 per arm); can ask model to compare across posts | New schema; harder to compare to prior work |

Recommendation: **per pair** for comparability with `api_baselines`; use batching only for stratified sampling, not for multi-post prompts (unless cost forces otherwise).

### 5.3 Prompt arms (ablation design)

**Control:**
- `STUDY_PROMPT_TEMPLATE` unchanged

**Category ablations (6 arms):**
- Control + "When evaluating, pay special attention to the following `{category}` signals: …"
- One arm per category, using that category's selected features only

**Combined ablations (progressive):**
- **Remove-skewed bundle:** categories/features with highest remove_rate (likely `surface_lexical` + `pragmatics_intent` + `target_directionality`)
- **Structure bundle:** `compositional_syntax` + `semantic_content` (keep-leaning argumentation cues)
- **Full selected set:** all category features that passed the selection workflow

**Optional theme-based arm:**
- Replace raw features with 8–12 merged canonical themes from stage 2 (natural-language moderation principles)

**Suggested first run (9 arms):**

| Arm | ID | Description |
| --- | --- | --- |
| Control | `control` | Study prompt only |
| Cat 1 | `surface_lexical` | Surface/lexical features only |
| Cat 2 | `topic_subject` | Topic features only |
| Cat 3 | `semantic_content` | Semantic features only |
| Cat 4 | `pragmatics_intent` | Pragmatics features only |
| Cat 5 | `target_directionality` | Target/directionality features only |
| Cat 6 | `compositional_syntax` | Syntactic features only |
| Combined remove | `combo_hostility` | Top remove-skewed features across cats 1, 4, 5 |
| Full | `full_selected` | All selected features across categories |

Defer `open_ended`-only and theme-only arms to round 2 unless round 1 shows a clear gap.

### 5.4 Prompt template shape (treatment)

Append a **moderation rubric block** after the existing study instructions, before the post pair:

```text
When making your decision, consider whether the posts exhibit any of the following
linguistic and rhetorical patterns (discovered from human linked-fate moderation):

[{category_name}]
- {feature_bullet_1}
- {feature_bullet_2}
...

Posts that exhibit remove-leaning patterns (e.g., {examples}) are more likely to warrant
removal, especially when multiple patterns co-occur. Posts that exhibit keep-leaning
patterns (e.g., {examples}) may still warrant removal if paired with hostility signals.
```

Keep rubric blocks **short** (≤150 words per category arm) to avoid context overflow.

### 5.5 Model and infrastructure

Reuse existing patterns:
- **Schema:** `IsRemoveResult` (`shared/schemas.py`)
- **Runner:** Extend `api_baselines/runner.py` or new experiment under `experiments/prompt_feature_ablation_2026_08_01/`
- **Model:** Start with one model (e.g., `gpt-5.4-nano` for parity with discovery, or best prior baseline from Exp 3 Bedrock runs)
- **Shuffle:** Deterministic Post 1/Post 2 blind (`render_user_prompt` seed)

### 5.6 Evaluation

| Metric | Notes |
| --- | --- |
| Accuracy, precision, recall, F1 | vs. modal gold label; per arm |
| Confusion matrix | Control vs. each treatment |
| ΔF1 vs. control | Primary success criterion for a treatment arm |
| Per-category error analysis | Where did feature prompts help/hurt? |
| Calibration | If we add probability later; not in v1 |

**Success criteria (draft):**
- A treatment arm beats control F1 by ≥ **2 pp** on the 500-post holdout
- Gains are not solely from trivial profanity keyword matching (spot-check false positives)
- Category ablations identify **which categories** drive improvement before running full combined prompt

---

## 6. Cost estimate (rough)

Assuming per-pair classification, 500 posts/arm, 9 arms:

| Item | Calls |
| --- | --- |
| Round 1 (9 arms) | 4,500 |
| + 2 theme/open-ended arms | +1,000 |
| Selection meta-LLM calls | ~50–100 (cheap relative to classification) |

Run control first; add treatment arms incrementally if cost is a concern.

---

## 7. Implementation phases

| Phase | Work | Output |
| --- | --- | --- |
| **0 — Selection** | Run feature filtering workflow (§4) on stage-1/stage-2 outputs | `selected_features_by_category.json` |
| **1 — Smoke** | 10 posts, control + 1 treatment, verify runner | Smoke pass |
| **2 — Category ablations** | 500 posts × (control + 6 categories) | Per-category ΔF1 table |
| **3 — Combined ablations** | 500 posts × combo arms | Best combined prompt |
| **4 — Write-up** | `RESULTS.md` + decision on whether to scale to full test set | Go/no-go for Phase 3 modeling |

---

## 8. Open decisions (need input)

1. **Per-pair vs. per-batch classification** — recommend per-pair for baseline comparability.
2. **Disjoint sample from discovery 50%?** — recommend yes; document overlap if unavoidable.
3. **Which model(s)?** — single model for v1, or replicate best Bedrock baseline too?
4. **Feature selection automation vs. human gate** — how much manual review before arms are frozen?
5. **Include interaction/cross-cutting themes in v1?** — or save for v2 after single-category signal is clear?
6. **Batch size 5** — confirm this is for sampling strata only, not multi-post prompts.

---

## 9. References

| Resource | Path / link |
| --- | --- |
| Feature generation experiment | `experiments/llm_based_feature_generation_2026_07_31/` |
| Production results | `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` |
| Control prompt | `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py` |
| Feature categories (source of truth) | `experiments/llm_based_feature_generation_2026_07_31/prompts.py` |
| Study history / LFP findings | `docs/runbooks/HISTORY_OF_STUDY.md` |
| Project overview | `docs/runbooks/WHAT_IS_MIRRORVIEW.md` |
| PR #33 | https://github.com/METResearchGroup/mirrorView-task/pull/33 |
