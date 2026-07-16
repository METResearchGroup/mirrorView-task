# Spec: Model Errors Analysis (Hard Post Pairs)

**Experiment dir:** `experiments/model_errors_analysis_2026_07_15/`  
**Parent study / modeling ladder:** `experiments/predict_keep_remove_2026_07_01/`  
**Primary question:** Which original/mirror post pairs are routinely hardest for our LLM API classifiers to get right?

This document is an implementation spec only. Do **not** run the analysis until this plan is accepted.

---

## Purpose

After the July 2026 keep/remove ladder, we want a single long table of per-post correctness across **LLM API runs only** (OpenAI `llm_api` + Bedrock zero-shot `api_baselines`), then analysis that isolates **hard pairs** (posts many models miss) and, for V1, whether Bedrock right vs wrong is linearly separable in Titan embedding space.

**V0 does not collect classical ML or encoder classifiers** (no logistic regression, XGBoost, ModernBERT, or other embedding-as-classifier families). Titan embeddings appear only later as **feature inputs for V1 Bedrock right-vs-wrong analysis**, not as a long-CSV classifier family.

---

## Scope

### In scope (V0 data product)

Collect labels + predictions into one long CSV from **LLM API experiment runs** under `experiments/predict_keep_remove_2026_07_01/` that:

1. Score the Study 2 training unit (one row per `message_id` / post pair with modal keep/remove label).
2. Use the **canonical study texts** (`original_text`, `mirror_text` from `keep_remove_results_2026_06_23.csv`) — no truncated / length-rewritten / regenerated stimulus ablations.
3. Belong to family **`bedrock`** or **`llm_api`** only.

### In scope (V1 analysis)

Bedrock zero-shot LLM baselines only (`models/llm_finetuning/api_baselines/`), because they use the study linked-fate prompt with both posts (blinded Post 1/Post 2 shuffle) — closest match to what participants saw.

V1 may load Titan embeddings from the existing embedding cache/feature helpers as **analysis features** for the Bedrock right-vs-wrong separator. Those embeddings are **not** a V0 classifier source and must not appear as long-CSV `family` values.

### Out of scope (for now)

- **Classical ML / embeddings classifiers:** `models/logistic_regression/`, `models/xgboost/`, and any `emb_ml/*` style long-CSV rows.
- **Encoder fine-tunes:** `models/modernbert/` (and similar).
- Length-matching / truncation experiments (`experiments/match_lengths_original_mirrors_2026_06_19/`, `experiments/truncate_posts_2026_06_19/`) as classification sources.
- May 2025 / May 2026 earlier keep/remove dirs except as embedding infra references for V1 (`experiments/simplified_predict_remove_2026_05_13/` if needed for cache docs).
- Implementing explainability / clustering writeups beyond what V1 needs (see `HOW_TO_DO_CLUSTERING.md`, `HOW_TO_DO_EXPLAINABILITY.md` for later).

---

## Background: data contract

### Source labels

| Artifact | Path |
| --- | --- |
| Raw trial CSV | `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` |
| Columns (raw) | `prolific_id`, `message_id`, `original_text`, `mirror_text`, `decision` |
| Training dataframe | `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` → `Dataloader().load_training_dataframe()` |

Training unit:

- One row per `message_id` (alias of `post_id`).
- Modal `decision` across raters; **ties → remove**.
- Label: `keep_remove_label` with `0=keep`, `1=remove`.
- ~8,791 unique post pairs.

Join keys for predictions: use `message_id` everywhere. Align `post_id == message_id` in the aggregator when needed.

Preferred long-CSV field name for the mirror column is `mirrored_text` (copy of `mirror_text`).

---

## Included data folders (concrete paths)

Paths are repo-relative from the worktree root. Only these trees feed the long CSV (plus labels above).

### Labels / study texts (always)

| Role | Path |
| --- | --- |
| Raw trials | `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` |
| Dataloader | `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` |

### A. Bedrock zero-shot LLM API (`family=bedrock`)

> **HARD CONSTRAINT — DO NOT RERUN BEDROCK.**  
> We **cannot** and **must not** call Bedrock / AWS Converse / `api_baselines/*/train.py` for this experiment. Use only the existing `predictions.csv` artifacts already present in this worktree (copied from the machine that originally ran Exp 3). Do **not** regenerate, resume, or re-invoke any Bedrock baseline.

| Role | Path |
| --- | --- |
| Root | `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/` |
| Aggregate metrics | `.../api_baselines/aggregate_outputs/aggregate_results.csv` |
| Aggregate narrative | `.../api_baselines/aggregate_outputs/aggregate_results.md` |
| Plots | `.../api_baselines/outputs/plot_results/2026_07_06-17:48:29/` |

**Completed full-dataset runs present (include in long CSV) — use these exact timestamp folders only:**

| Variant | Run dir (this worktree) | Rows |
| --- | --- | --- |
| Ministral 8B | `.../api_baselines/ministral-3-8b-instruct/outputs/2026_07_06-15:52:37/` | 8791 (+ header → 8792 lines) |
| Ministral 14B | `.../api_baselines/ministral-3-14b-instruct/outputs/2026_07_06-16:12:54/` | 8791 (+ header → 8792 lines) |
| Qwen3 32B | `.../api_baselines/qwen3-32b/outputs/2026_07_06-16:35:49/` | 8791 (+ header → 8792 lines) |
| Qwen3 Next 80B | `.../api_baselines/qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/` | 8791 (+ header → 8792 lines) |

Each included run dir has `predictions.csv`, `metadata.json`, `metrics.json` (plus companion `prompt_template.txt` / `run_command.txt`).

**Do not use** incomplete Ministral-8B smoke/partial runs if present elsewhere: `2026_07_06-15:40:13`, `2026_07_06-15:40:33`.

Bedrock IDs: `mistral.ministral-3-8b-instruct`, `mistral.ministral-3-14b-instruct`, `qwen.qwen3-32b-v1:0`, `qwen.qwen3-next-80b-a3b`.

Stimulus: Study prompt + original **and** mirror texts; deterministic Post 1/Post 2 shuffle (`prompts.py`). Pred columns: `message_id`, `keep_remove_label`, `predicted_label` (no probability).

**Status in this worktree:** all four complete `predictions.csv` artifacts are present at the timestamp paths above. Bedrock long-CSV rows and V1 are **unblocked**. **Do not** call Bedrock again.

### B. OpenAI LLM API prompting (`family=llm_api`)

| Role | Path |
| --- | --- |
| Root | `experiments/predict_keep_remove_2026_07_01/models/llm_api/` |
| Aggregate (reference only) | `.../llm_api/aggregate_outputs/aggregate_results.csv` |

**Completed full-dataset runs present (include in long CSV):**

| Run dir | Rows | Notes |
| --- | --- | --- |
| `experiments/predict_keep_remove_2026_07_01/models/llm_api/one_shot/original/small/outputs/2026_07_03-18:30:51/` | train 7032 + test 1759 | `limit: null`; model `gpt-5.4-nano`; `input_mode=original` |
| `experiments/predict_keep_remove_2026_07_01/models/llm_api/one_shot/original_plus_mirror/small/outputs/2026_07_03-18:30:14/` | train 7032 + test 1759 | `limit: null`; model `gpt-5.4-nano`; `input_mode=original_plus_mirror` |

Each included run dir has `train_predictions.csv`, `test_predictions.csv`, `metadata.json`, `metrics.json`.

Pred columns: `message_id`, `keep_remove_label`, `predicted_label`, `predicted_remove_probability`. Models: `small` → `gpt-5.4-nano`; `large` → `gpt-5.5` (`constants.py`) — only `small` full runs exist here.

**Exclude (present but incomplete / smoke / cost-skipped):**

- Other timestamp dirs under `one_shot/...` and all of `few_shot/...` (smoke `--limit`, partial CSVs, or incomplete resume fragments). Example smoke: `.../one_shot/original/small/outputs/2026_07_03-18:20:16/` (`limit: 8`).
- Documented cost-skipped variants (few-shot / large) — no complete full-dataset artifacts suitable for inclusion.

**Stimulus note:** both `original` and `original_plus_mirror` use canonical study text; `original` simply omits the mirror from the prompt (input ablation, not text rewrite). Include both in the long CSV. For “matches what users saw,” prefer `original_plus_mirror` (and Bedrock).

### C. V1-only analysis inputs (not long-CSV classifier sources)

| Role | Path |
| --- | --- |
| Embedding cache loader | `experiments/predict_keep_remove_2026_07_01/embeddings/cache_loader.py` |
| Feature helpers | `experiments/predict_keep_remove_2026_07_01/embeddings/features/concat_cosine.py` |
| | `experiments/predict_keep_remove_2026_07_01/embeddings/features/only_original.py` |

Use these **only** when building the V1 Bedrock right-vs-wrong separator. Do **not** treat logistic/XGBoost train trees as V0 sources.

---

## Inclusion / exclusion rules

### Include a run if all of the following hold

1. Predictions file(s) exist with `message_id` (or `post_id`) and `predicted_label`.
2. Labels match `keep_remove_label` from `load_training_dataframe()` (or are identical when joined).
3. Stimulus texts are the Study 2 canonical texts (no truncate / length-match rewrites).
4. `family` is `bedrock` or `llm_api`.
5. Run is complete for the unit being analyzed:
   - Bedrock: full `predictions.csv` with ~8,791 rows (or documented subset with `metadata.json` clarifying intent).
   - LLM API: prefer runs where `limit is null` and `|train|+|test| = 8791`.

### Exclude

| Pattern | Why |
| --- | --- |
| Logistic / XGBoost / ModernBERT / any non-LLM-API family | Out of V0 scope |
| LLM API / Bedrock smoke (`--limit N`) | Not comparable |
| Incomplete resume fragments | Partial coverage biases hard-pair rates |
| Feature runs on non-canonical text | Stimulus changed |
| Aggregate-only CSV/MD without row preds | Cannot compute `is_correct` |

### Canonical run selection when multiple timestamps exist

Pick the newest run under each variant folder where:

- `metadata.json` has no `limit` (or `limit: null`), and
- prediction row count matches expected `n_train` / `n_test` / `n_total`, and
- `metrics.json` exists.

Record chosen paths in `outputs/run_manifest.json`. For the two full `llm_api` runs above, those timestamps are already the complete ones to record.

---

## Target long CSV schema

**Path:** `experiments/model_errors_analysis_2026_07_15/outputs/classifier_post_results_long.csv`

The long CSV uses **only** the columns below (no extra audit columns).

| Column | Type | Definition |
| --- | --- | --- |
| `post_id` | str | Same as `message_id` from the study dataframe |
| `original_text` | str | Canonical original |
| `mirrored_text` | str | Canonical mirror (`mirror_text`) |
| `label` | int | `keep_remove_label` (`0=keep`, `1=remove`) |
| `classifier_id` | str | Stable slug (see families above) |
| `family` | str | **`bedrock`** or **`llm_api` only** |
| `ablation` | str | Ablation / condition encoding (see below) |
| `is_correct` | bool/int | `1` iff `predicted_label == label` |

One row = one `(post_id, classifier_id)` evaluation. If a classifier only predicted on test, only test rows appear for that `classifier_id`. Prefer including train+test for `llm_api` (hard-pair rates can later filter conceptually if needed; with this schema there is no `split` column — include all scored rows from the chosen run, deduped on `(post_id, classifier_id)` after concat so train and test do not collide).

### Populating `ablation`

Encode the experimental condition as a single pipe-delimited string of `key=value` pairs (stable order). Required keys:

| Family | `ablation` contents |
| --- | --- |
| `bedrock` | `provider=bedrock\|model=<variant_folder>\|bedrock_model_id=<id>\|prompt=linked_fate_both_posts\|input_mode=original_plus_mirror` |
| `llm_api` | `provider=openai\|model=<model_name>\|model_size=<small\|large>\|prompt_type=<one_shot\|few_shot>\|input_mode=<original\|original_plus_mirror>` |

Examples:

- Bedrock Qwen3 32B: `provider=bedrock|model=qwen3-32b|bedrock_model_id=qwen.qwen3-32b-v1:0|prompt=linked_fate_both_posts|input_mode=original_plus_mirror`
- LLM API original-only small: `provider=openai|model=gpt-5.4-nano|model_size=small|prompt_type=one_shot|input_mode=original`
- LLM API original+mirror small: `provider=openai|model=gpt-5.4-nano|model_size=small|prompt_type=one_shot|input_mode=original_plus_mirror`

### Suggested `classifier_id`s

| `classifier_id` | `family` | Source run |
| --- | --- | --- |
| `bedrock/ministral-3-8b-instruct` | `bedrock` | `.../api_baselines/ministral-3-8b-instruct/outputs/2026_07_06-15:52:37/` |
| `bedrock/ministral-3-14b-instruct` | `bedrock` | `.../api_baselines/ministral-3-14b-instruct/outputs/2026_07_06-16:12:54/` |
| `bedrock/qwen3-32b` | `bedrock` | `.../api_baselines/qwen3-32b/outputs/2026_07_06-16:35:49/` |
| `bedrock/qwen3-next-80b-a3b` | `bedrock` | `.../api_baselines/qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/` |
| `llm_api/one_shot/original/small` | `llm_api` | `.../one_shot/original/small/outputs/2026_07_03-18:30:51/` |
| `llm_api/one_shot/original_plus_mirror/small` | `llm_api` | `.../one_shot/original_plus_mirror/small/outputs/2026_07_03-18:30:14/` |

---

## Aggregation pipeline (implementation steps)

Suggested package layout (implement later):

```text
experiments/model_errors_analysis_2026_07_15/
  spec.md                          # this file
  README.md                        # short how-to (after implement)
  collect/
    manifest.py                    # enumerate eligible runs → run_manifest.json
    load_predictions.py            # bedrock + llm_api adapters only
    build_long_csv.py              # join texts + labels → long CSV
  analyze/
    hard_pairs.py                  # error-rate / co-miss tables
    v1_bedrock_separability.py     # linear + 2D reduction
  outputs/                         # gitignore bulk artifacts if large
```

### Step 0 — Confirm existing prediction artifacts (no Bedrock re-run)

1. **Bedrock (REQUIRED POLICY):** Use **only** the four copied timestamp folders listed in §A. Read their existing `predictions.csv` files. **Do not** call Bedrock, AWS Converse, or any `api_baselines/*/train.py`. **Do not** regenerate or resume Bedrock baselines. Incomplete Ministral-8B timestamps `2026_07_06-15:40:13` / `2026_07_06-15:40:33` must stay excluded.
2. **LLM API:** The two full `one_shot/.../small` runs listed above are already present — no regeneration needed for V0 of those classifiers.

Do **not** regenerate logistic / XGBoost / ModernBERT predictions for this experiment. Do **not** regenerate Bedrock predictions.

### Step 1 — Build run manifest

Write `outputs/run_manifest.json` listing each included `classifier_id`, `family`, `ablation`, run_dir, row counts, and source prediction filename(s).

### Step 2 — Normalize predictions

Per family adapter (**only** these two):

- Bedrock: read `predictions.csv`; all rows scored (no train/test cut in current runner).
- LLM API: concat `train_predictions.csv` + `test_predictions.csv`, then keep unique `(post_id, classifier_id)` (train and test partitions are disjoint by construction).

Compute `is_correct = (predicted_label == keep_remove_label)`. Set `family` and `ablation` per the schema rules above.

### Step 3 — Join texts

Left-join canonical texts from `Dataloader().load_training_dataframe()` on `message_id` / `post_id`. Fail loudly on missing IDs or text mismatch.

### Step 4 — Emit long CSV + sanity checks

Assert:

- Columns are exactly the target schema (no extras).
- `family` values ⊆ `{bedrock, llm_api}`.
- No duplicate `(post_id, classifier_id)`.
- `label` distribution matches training dataframe.
- Per-classifier accuracy recomputed from the long CSV matches that run’s `metrics.json` within rounding tolerance (especially Bedrock aggregate and LLM API test metrics).

### Step 5 — Hard-pair slicing helpers (V0 analysis product)

From the long CSV, produce at least:

| Artifact | Description |
| --- | --- |
| `outputs/post_error_rates.csv` | Per `post_id`: `n_classifiers`, `n_wrong`, `error_rate`, `label`, texts |
| `outputs/hard_pairs_top_k.csv` | Top-K by `error_rate` (and ties by `n_wrong`) |
| `outputs/co_miss_matrix.csv` | Optional: pairwise classifier agreement on errors |
| `outputs/family_slice_summary.md` | Error rates by `family` / `classifier_id` / notable `ablation` dims |

“Routinely hardest” default definition: posts with `error_rate == 1.0` across all included classifiers that scored that post; secondary: highest `n_wrong` among posts scored by ≥ N classifiers (default N = number of V0-included complete classifiers).

---

## V1 analysis plan — Bedrock right vs wrong separator

**Goal:** For Bedrock zero-shot predictions only, ask whether Titan embeddings linearly separate posts the LLM got right vs wrong, and whether that structure is visible in 2D.

### V1 classifier filter

- Family = `bedrock`.
- Include all four models that have complete `predictions.csv`.
- **Primary target for the separator:** per-post majority vote across Bedrock models — `bedrock_majority_correct` — so one label per post.  
  **Alternative (report both):** pool all `(post_id, classifier_id)` rows (repeated embeddings) and train on stacked rows; also run per-model separators for Ministral 14B / Qwen3 32B / Qwen3 Next 80B (skip Ministral 8B as primary — extreme remove-conservative recall makes “wrong” dominated by remove misses).

Assumption to confirm: V1 “Bedrock LLM API only” means `api_baselines` (not OpenAI `llm_api`). If stakeholders meant OpenAI `original_plus_mirror` instead/additionally, reuse the same pipeline with `family=llm_api` + `classifier_id=llm_api/one_shot/original_plus_mirror/small`.

### Embeddings source (analysis input only)

Reuse existing Titan embeddings as **features for the right-vs-wrong linear probe**, **do not** re-embed unless cache miss, and **do not** add embedding/ML classifiers to the long CSV:

```bash
# Analysis-only feature path (not a V0 classifier family):
experiments/predict_keep_remove_2026_07_01/embeddings/cache_loader.py
# model: amazon.titan-embed-text-v2:0, dims=256, normalize=True
# S3: jspsych-mirror-view-3
# DDB: jspsych-mirror-view-embedding-cache
```

Feature vector for V1 (lock in metadata):

1. **Primary:** `concat_cosine` → `[orig_emb (256), mirror_emb (256), cosine (1)]` shape `(513,)` — both posts present, matches study pair.
2. **Ablation (optional):** `only_original` `(256,)` — diagnostically compare if errors are original-only.

Build via existing feature helpers:

- `embeddings/features/concat_cosine.py`
- `embeddings/features/only_original.py`

Clarification: fitting a logistic regression **on Titan features to predict Bedrock is_error** is part of V1 analysis. It is **not** the keep/remove logistic models under `models/logistic_regression/` and must not be confused with V0 long-CSV collection.

### Train / eval (right vs wrong)

Target: `y = 1` if Bedrock prediction(s) **wrong**, `y = 0` if **correct** (or invert and document; prefer `is_error` as positive class so precision/recall speak about hard cases).

Protocol:

1. Join embeddings to posts Bedrock scored.
2. Stratified train/test split by `post_id` (`seed=42`, `train_split=0.8`). Do **not** leak the same post across splits.
3. Fit **logistic regression** (`class_weight='balanced'`) predicting `is_error` from Titan features.
4. Report train/test accuracy, ROC-AUC, PR-AUC, confusion matrix for error class.
5. Save `outputs/v1_bedrock/linear_separator_metrics.json`, coefficients or top-|coef| dims, and predictions CSV.

Interpretation guardrail: high AUC means errors are linearly organized in embedding space; low AUC means hard pairs are not a single half-space of Titan features.

### 2D reduction + visualization

On the same feature matrix (prefer train+test all points, fit reduction on train only to avoid optimism):

1. Standardize features.
2. Run **PCA (2D)** and **linear discriminant / LDA projected to 1–2D** (LDA is the linear separator view). Optionally t-SNE/UMAP as secondary *nonlinear* viz (do not claim linear separation from them).
3. Scatter plots colored by correct vs wrong (and optionally by `label` keep/remove as small multiples).
4. Overlay the logistic decision boundary in the 2D PCA plane (project the hyperplane approx / show predicted region).

Artifacts:

- `outputs/v1_bedrock/pca_right_vs_wrong.png`
- `outputs/v1_bedrock/lda_right_vs_wrong.png`
- `outputs/v1_bedrock/embeddings_2d.csv` (`post_id`, `pc1`, `pc2`, `is_correct`, `label`, …)

### V1 success criteria

- Pipeline runs end-to-end from long CSV (bedrock rows) + embedding cache.
- Metrics + plots written under `outputs/v1_bedrock/`.
- Short markdown note `outputs/v1_bedrock/README.md` stating whether a linear separator appears strong (e.g. test AUC ≫ 0.5) and pointing at hardest posts from `hard_pairs_top_k.csv` that Bedrock missed.

---

## Outputs / artifacts checklist

| Path | Producer |
| --- | --- |
| `outputs/run_manifest.json` | collect |
| `outputs/classifier_post_results_long.csv` | collect |
| `outputs/post_error_rates.csv` | analyze |
| `outputs/hard_pairs_top_k.csv` | analyze |
| `outputs/v1_bedrock/linear_separator_metrics.json` | V1 |
| `outputs/v1_bedrock/pca_right_vs_wrong.png` | V1 |
| `outputs/v1_bedrock/lda_right_vs_wrong.png` | V1 |
| `outputs/v1_bedrock/embeddings_2d.csv` | V1 |
| `outputs/v1_bedrock/README.md` | V1 writeup |

---

## Open questions / assumptions

1. **Bedrock predictions are present — do not re-run**  
   Resolved: all four complete `predictions.csv` files are in this worktree at the §A timestamp paths. **Must not** call Bedrock / `api_baselines/*/train.py`. Analysis consumes those CSVs only.

2. **What “original text” filter means for LLM input modes**  
   Assumption: exclude stimulus *rewrites*, **include** `original` and `original_plus_mirror` prompting ablations (canonical text). For “user-matching stimulus,” prioritize Bedrock and `original_plus_mirror`. Encode input mode in `ablation`.

3. **Train vs test rows in the long CSV**  
   Assumption: for `llm_api`, include both train and test scored posts (disjoint); Bedrock scored all rows without a train/test cut. There is no `split` column in the long CSV.

4. **`mirrored_text` vs `mirror_text`**  
   Source column is `mirror_text`. Spec uses `mirrored_text` in the long CSV as requested; map explicitly in the builder.

5. **V1 “Bedrock LLM API” naming**  
   Assumption: means `models/llm_finetuning/api_baselines/` (Bedrock Converse), not `models/llm_api/` (OpenAI). Confirm with stakeholder if OpenAI original-plus-mirror should be co-primary.

6. **Positive class for V1 separator**  
   Assumption: predict `is_error` (wrong=1) so metrics emphasize hard cases.

7. **No classical ML in V0**  
   Assumption confirmed by scope: do not wait on or regenerate logistic/XGBoost/ModernBERT prediction CSVs for the long table. Titan embeddings remain V1 analysis input only.

---

## Implementation order (when executing)

1. Confirm the four Bedrock timestamp folders in §A and the two full `llm_api` runs exist (read-only). **Do not** call Bedrock.
2. `collect/manifest.py` + `collect/load_predictions.py` + `collect/build_long_csv.py` + sanity checks vs `metrics.json`.
3. Hard-pair rate tables.
4. V1 Bedrock embedding linear separator + PCA/LDA plots (analysis-only Titan features).
5. Short README in this experiment dir documenting commands and artifact paths.

### V0 long CSV (implemented)

```bash
cd experiments/model_errors_analysis_2026_07_15
uv run python collect/build_long_csv.py
# → outputs/run_manifest.json
# → outputs/classifier_post_results_long.csv  (6 × 8791 = 52746 rows)
```

### Commands / policy for later (do not run inference)

```bash
# DO NOT run any api_baselines/*/train.py or otherwise call Bedrock/AWS.
# Use the copied predictions.csv artifacts only, e.g.:
#   .../ministral-3-8b-instruct/outputs/2026_07_06-15:52:37/predictions.csv
#   .../ministral-3-14b-instruct/outputs/2026_07_06-16:12:54/predictions.csv
#   .../qwen3-32b/outputs/2026_07_06-16:35:49/predictions.csv
#   .../qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/predictions.csv
```

---

## References

- `experiments/predict_keep_remove_2026_07_01/PROPOSAL.md`
- `experiments/predict_keep_remove_2026_07_01/README.md`
- `experiments/predict_keep_remove_2026_07_01/HOW_TO_TRAIN_LANGUAGE_MODELS.md` (Exp 1–3 results)
- `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/README.md`
- `docs/plans/2026-07-06_exp3_bedrock_zero_shot_baselines_628401/IMPLEMENTATION_PLAN.md`
- `experiments/predict_keep_remove_2026_07_01/embeddings/README.md` (V1 feature cache only)
- `experiments/predict_keep_remove_2026_05_07/PLAN_BUILD_DEEP_MODEL.md` (doc style reference)
