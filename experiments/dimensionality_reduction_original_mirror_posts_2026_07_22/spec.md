# Spec: PCA/LDA of original vs mirrored Titan embeddings

**Experiment dir:** `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/`  
**Parent study:** `experiments/predict_keep_remove_2026_07_01/`  
**Reference:** `experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py`  
**Plan:** `docs/plans/2026-07-22_dimensionality_reduction_original_mirror_418754/plan.md`

## Purpose

Visualize Titan text embeddings of **original** vs **mirrored** post texts with PCA/LDA.
Each study `post_id` contributes two 256-d vectors stacked into a long `(2N, 256)` matrix
with binary label `is_mirrored`. Reductions are fit on **all** rows (no train/test split).

## Forbidden in v1

- Calling Bedrock embed, Converse, or `api_baselines/*/train.py`
- Loading embeddings from S3 / DynamoDB
- Writing under `experiments/model_errors_analysis_2026_07_15/`
- Introducing a train/test split or Train|Test plot panels

## Paths (`analyze/paths.py`)

| Constant | Value |
|----------|-------|
| `FEATURE_SET` | `original_and_mirror_long` |
| `EMBEDDING_DIM` | `256` |
| `LDA_TARGET` | `is_mirrored` |
| Primary cache | `experiments/predict_keep_remove_2026_07_01/embedding_cache/` |
| Optional backup | `/Users/mark/Documents/work/mirrorView-task/.../embedding_cache/` |

## Long-table schema

| Column | Type | Invariant |
|--------|------|-----------|
| `post_id` | str | Exactly **2** rows per post_id |
| `text_role` | str | ∈ `{"original_text", "mirror_text"}` |
| `is_mirrored` | int | `0` iff original; `1` iff mirror |
| `label` | int | keep/remove (`0=keep`, `1=remove`); identical on both rows of a post |

## Matrix

- `X_original_and_mirror.npy`: `float64`, shape `(len(meta), 256)`, row-aligned with meta.
- No Qwen / `is_correct` / `is_error` columns.

## Fit

- `StandardScaler`, `PCA(2)`, `LDA(1; y=is_mirrored)`, and residual PC1 ⊥ LD1 are fit on **all** rows.
- Plots are single-panel (no Train|Test).

## Plot / color contract

| Class | `is_mirrored` | Color | Marker |
|-------|---------------|-------|--------|
| original | 0 | `#2A9D8F` | `o` |
| mirrored | 1 | `#E76F51` | `x` |

Axis labels: `LD1 (target=is_mirrored)`, `Residual PC1 ⊥ LD1` (no “fit on train” wording).

Titles: **original vs mirrored** / **Titan original+mirror long matrix** — never “Qwen” / “right vs wrong”.
