# RESULTS — Model Errors Analysis V1 (2026-07-15)

**Classifier:** Bedrock Qwen3 Next 80B (`bedrock/qwen3-next-80b-a3b`)  
**Features:** original-post Titan embeddings only (`only_original`, 256-d)  
**Artifacts:** `outputs/v1_bedrock/`

---

## 1. Executive summary

Qwen3 Next 80B is wrong on about **36%** of Study 2 posts (accuracy ≈ **64.1%** on 8,791 pairs). A balanced logistic probe on original-post Titan embeddings predicts those errors only weakly out of sample (**test ROC-AUC ≈ 0.60**, accuracy ≈ **0.57**). PCA of the same features shows almost no right/wrong structure in 2D; LDA shows mild supervised separation that shrinks on the held-out set. **Conclusion:** Qwen right-vs-wrong is not a strong linear half-space in original Titan space — there is a weak but nonzero linear signal, not a cleanly separable error regime.

---

## 2. Key findings

1. **Base model error rate is substantial.** Of 8,791 posts, 3,152 are errors (`is_error` rate **0.3585**); 5,639 are correct (accuracy **0.6415**).
2. **Linear probe beats chance only modestly.** Test ROC-AUC **0.5995** (train **0.6543**); test accuracy **0.5713** vs stratified error base rate ~0.36.
3. **2D PCA does not reveal error clusters.** PC1+PC2 explain only **~5.05%** of Titan variance; a 2D logistic overlay in the PC plane has test accuracy **0.562**.
4. **Supervised LDA is weak but real.** Test LD1 Cohen’s *d* (wrong − correct) **0.329** (train **0.558**); midpoint-threshold accuracy **0.567** on test.
5. **Shared split was respected.** One stratified 80/20 split (`seed=42`) drives both logistic and 2D branches; no re-split; no Bedrock re-run.

---

## 3. Results

### 3.1 Data and split

| Item | Value |
| --- | --- |
| Labels source | `outputs/base_model_llm_labels.csv` (`bedrock/qwen3-next-80b-a3b` only) |
| N posts | 8,791 |
| Correct / error | 5,639 / 3,152 |
| Qwen accuracy / error rate | 0.6415 / 0.3585 |
| Features | `only_original` Titan `amazon.titan-embed-text-v2:0`, dim 256, normalized |
| Embedding cache | 8,791/8,791 local hits; AWS not called |
| Split | `seed=42`, `train_split=0.8`, stratify on `is_error` |
| Train / test | 7,032 / 1,759 (disjoint; union = full set) |
| Train / test error rate | 0.3585 / 0.3587 |

Artifacts: `analysis_table.parquet`, `X_only_original.npy` `(8791, 256)`, `split_ids.json`.

### 3.2 Logistic separator (V1.3A)

Pipeline: `StandardScaler` → `LogisticRegression(class_weight='balanced', solver=lbfgs)`, positive class = `is_error`. Fit on train IDs only; evaluate on test IDs from `split_ids.json`.

| Split | N | Accuracy | ROC-AUC | PR-AUC | Precision (error) | Recall (error) | F1 (error) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 7,032 | 0.6027 | 0.6543 | 0.4884 | 0.4591 | 0.6081 | 0.5232 |
| **Test** | **1,759** | **0.5713** | **0.5995** | **0.4308** | **0.4276** | **0.5753** | **0.4905** |

**Test confusion** (rows = true correct/error; cols = pred correct/error; error = 1):

|  | Pred correct (0) | Pred error (1) |
| --- | ---: | ---: |
| True correct (0) | TN 642 | FP 486 |
| True error (1) | FN 268 | TP 363 |

Largest |coefficients| are small in magnitude (top |coef| ≈ 0.106 on dim 38) — no single Titan dimension dominates.

Source: `linear_separator_metrics.json` (alias `logistic_metrics.json`).

### 3.3 2D reduction (V1.3B)

Leakage-safe: scaler / PCA / LDA fit on **train only**, then transform train+test.

**PCA (2D)**

| Metric | Value |
| --- | --- |
| PC1 / PC2 explained variance | 2.90% / 2.15% |
| Cumsum (2 PCs) | 5.05% |
| 2D logistic overlay (PC1/PC2) train / test accuracy | 0.562 / 0.562 |

Plots (`pca_right_vs_wrong.png`): right and wrong clouds heavily overlap; no clear linear partition in the PC plane.

**LDA (1 discriminant; y-axis = residual PC1 ⊥ LD1)**

| Metric | Train | Test |
| --- | ---: | ---: |
| Mean LD1 (correct) | −0.200 | −0.117 |
| Mean LD1 (wrong) | 0.358 | 0.224 |
| Cohen’s *d* (wrong − correct) | 0.558 | 0.329 |
| Midpoint-threshold accuracy | 0.605 | 0.567 |

Plots (`lda_right_vs_wrong.png`): mild shift along LD1 on train that attenuates on test — consistent with the ~0.60 test ROC-AUC of the full 256-d logistic.

Source: `reduction_summary.json`, `pca_variance_explained.json`, `embeddings_2d.csv`.

---

## 4. Method (brief)

1. **Labels:** reuse existing Bedrock Qwen3 Next 80B predictions (`2026_07_06-16:57:43`); `is_error = 1 − is_correct`. **Do not** re-call Bedrock.
2. **Features:** join original-post Titan vectors via `only_original` (no mirror / concat / cosine features).
3. **Split once:** stratified post-level 80/20 → `split_ids.json`.
4. **Parallel branches on the same IDs:**
   - **V1.3A** — balanced logistic on 256-d Titan → metrics / coefs / predictions.
   - **V1.3B** — PCA + LDA viz (fit-on-train) → plots + 2D coords.

Scripts: `analyze/v1_build_table.py`, `v1_split.py`, `v1_linear_separator.py`, `v1_embed_2d.py`.

---

## 5. Caveats

- **Weak linear signal.** Test ROC-AUC ≈ 0.60 is above chance but far from a strong separator; hard pairs are not a single half-space of original Titan features.
- **PCA is not the right lens here.** Two PCs capture ~5% variance; visual non-separation in PCA does not by itself prove absence of higher-dimensional linear structure (the 256-d probe is the better summary).
- **LDA overfits the train axis somewhat.** Train Cohen’s *d* 0.56 → test 0.33; report test metrics as primary.
- **No Bedrock re-run.** Results depend on the copied `predictions.csv` and the local Titan embedding cache already present for this study.
- **Feature scope is narrow by design.** Mirror embeddings, concat/cosine, and nonlinear probes are out of V1 scope — a stronger separator might exist under other feature sets, but that is a later question.
- **Hard-pair tables** (`post_error_rates.csv`, etc.) from the V0 checklist were not required for this V1 separability pass.

---

## Artifact index

| Path | Role |
| --- | --- |
| `outputs/base_model_llm_labels.csv` | Qwen right/wrong labels |
| `outputs/v1_bedrock/analysis_table.parquet` | Joined labels + embeddings |
| `outputs/v1_bedrock/split_ids.json` | Shared train/test IDs |
| `outputs/v1_bedrock/linear_separator_metrics.json` | Logistic metrics |
| `outputs/v1_bedrock/pca_right_vs_wrong.png` | PCA scatter |
| `outputs/v1_bedrock/lda_right_vs_wrong.png` | LDA scatter |
| `outputs/v1_bedrock/reduction_summary.json` | PCA/LDA numeric summary |
| `outputs/v1_bedrock/progress_updates*.md` | Pipeline progress notes |
