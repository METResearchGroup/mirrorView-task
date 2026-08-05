# Build a four-stage BERTopic pipeline on Titan original-post embeddings under `experiments/bertopic_modeling_2026_08_05/`

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Delegated tasks must be impossible to misread.

## Overview

Stand up the experiment described in `experiments/bertopic_modeling_2026_08_05/README.md`: load Study Phase 2 Part 2 modal keep/remove posts via `shared/data/dataloader.py` (`STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`), resolve precomputed Amazon Titan Text Embeddings V2 vectors (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized) into a committed local cache under `experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/`, fit BERTopic on **all original-text posts** with embeddings passed in explicitly (no re-embedding inside BERTopic), write c-TF-IDF topic artifacts without calling an LLM, then label topics post-hoc with OpenAI (`gpt-5.4-nano` via `bertopic.representation.OpenAI`), and emit three 2-D cluster maps (by topic, by keep/remove, by unanimous vs not) from one shared UMAP projection. Unanimous labels come from a join to `STUDY_PHASE_2_PART_2_RESULTS_FULL`; keep/remove and unanimous are visualization overlays only — they never enter the fit.

**Workspace note:** the experiment folder currently holds only `README.md`. This plan creates the pipeline from scratch. Related sibling: `experiments/create_llm_features_2026_08_05/` clusters **LLM-generated feature** embeddings by keep/remove class; this experiment clusters **post** embeddings with BERTopic on the full original corpus.

**Out of scope (v1):** mirror-text BERTopic under `outputs/**/mirror/`; `export_features.py` for downstream keep/remove classifiers; any non-Titan embedding model inside BERTopic.

**Files that will be added** (exact paths):

| Path | Role |
| --- | --- |
| `experiments/bertopic_modeling_2026_08_05/src/__init__.py` | Package marker |
| `experiments/bertopic_modeling_2026_08_05/src/paths.py` | Experiment roots; text role fixed to `original` in v1 |
| `experiments/bertopic_modeling_2026_08_05/src/data.py` | Load keep/remove labels; join unanimous flag from results full |
| `experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` | Stage 1: resolve Titan vectors into local cache (no Bedrock when complete) |
| `experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | Stage 2: fit_transform with passed embeddings; c-TF-IDF + UMAP-2D; no LLM |
| `experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py` | Stage 3: post-hoc OpenAI topic labels; skip noise topic |
| `experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py` | Stage 4: three Plotly HTML + PNG overlays from shared UMAP-2D |
| `experiments/bertopic_modeling_2026_08_05/RESULTS.md` | Written after the production full-corpus run |
| `experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/` | Committed Titan cache (`embeddings.npy`, `index.parquet`, `metadata.json`) |
| `experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>/` | Stage-2 run artifacts (assignments, topic info, umap_2d, model) |
| `experiments/bertopic_modeling_2026_08_05/outputs/labels/original/<UTC_TS>/` | Stage-3 LLM labels + provenance |
| `experiments/bertopic_modeling_2026_08_05/outputs/figures/original/<UTC_TS>/` | Stage-4 HTML + PNG figures |

**Dependency change:** declare `bertopic` (and its usual UMAP/HDBSCAN pull-ins as that package requires) as an **optional** `[project.optional-dependencies]` extra named `bertopic` in `pyproject.toml` — same pattern as the existing `modernbert-training` extra. Do **not** add it to the default `dependencies` list or the `dev` dependency group. Operators install with `uv sync --extra bertopic` and run stages with `PYTHONPATH=. uv run --extra bertopic python …`. Reuse `openai` / repo-root `.env` `OPENAI_API_KEY` for labeling. Reuse AWS credentials only for optional embedding-cache backfill.

**Not changed:** `shared/data/`, `shared/embeddings/bedrock.py`, `shared/schemas.py`. No mirror outputs in v1.

## Happy flow

An operator installs the optional `bertopic` extra, builds the local Titan embedding cache for all original posts (Bedrock only if rows are missing), smoke-tests fit → LLM label → three viz overlays on a fixed **50-post** sample, gets explicit approval, then runs the same stages on the full original corpus and records outcomes in `RESULTS.md`.

```mermaid
flowchart TD
  A[Load STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS] --> B[load_embeddings: cache Titan original vectors]
  B --> S[Smoke: 50-post fit + label + viz]
  S --> AP{User approves smoke?}
  AP -->|no| STOP[Stop]
  AP -->|yes| C[fit_bertopic on all original posts]
  C --> D[label_topics_llm post-hoc]
  D --> E[visualize: topic / keep-remove / unanimous]
  E --> F[RESULTS.md]
```

## Approach

Keep stages isolated so UMAP/HDBSCAN retunes never re-spend OpenAI calls: embeddings and fit produce durable artifacts; LLM labeling is a separate, pointer-linked run; visualization reuses the fit-time 2-D UMAP and only recolors. Pass Titan vectors into BERTopic explicitly. Fit on the full original corpus for production; keep/remove and unanimous join only for overlays. Prefer parquet/npy/json artifacts; gitignore large saved model dirs if needed. Keep BERTopic off the default/dev install path so unrelated workflows stay lean.

## Steps

Detail for each step will live under `steps/` after this draft is confirmed.

### Step 1: Scaffold package, paths, data join, and optional dependencies

Create `experiments/bertopic_modeling_2026_08_05/src/` with `__init__.py`, `paths.py`, and `data.py` (keep/remove load + unanimous join from `STUDY_PHASE_2_PART_2_RESULTS_FULL`, rule recorded in run metadata). Add a `bertopic` entry under `[project.optional-dependencies]` in `pyproject.toml` (mirror the `modernbert-training` extra shape; allow bertopic’s usual UMAP/HDBSCAN transitive deps; do not touch default `dependencies` or `dependency-groups.dev`). Document stage CLI order in the existing README, including `uv sync --extra bertopic` and `uv run --extra bertopic` (commands only).

### Step 2: Implement Titan embedding cache loader

Implement `experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py`: default path loads a complete `outputs/embeddings/original/` cache; `--backfill` fills missing `message_id` rows via `shared/embeddings/bedrock.py` only. Cache holds vectors + id index; post text always reloads from the dataset by `message_id`.

### Step 3: Implement BERTopic fit (no LLM)

Implement `experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py`: `fit_transform` with embeddings passed in, UMAP + HDBSCAN + CountVectorizer settings from the README, soft probabilities on, write timestamped artifacts under `outputs/topics/original/<UTC_TS>/` including assignments, c-TF-IDF topic info, optional probability matrix, `umap_2d.npy`, saved model, and `metadata.json`.

### Step 4: Implement post-hoc LLM topic labeling

Implement `experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py`: `update_topics` with `bertopic.representation.OpenAI` (`gpt-5.4-nano`, prompt shape from README), skip noise topic `-1`, write under `outputs/labels/original/<UTC_TS>/` with pointer to the source topics run.

### Step 5: Implement three-overlay cluster visualizations

Implement `experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py`: load one shared `umap_2d.npy` plus assignments and overlay columns; emit Plotly HTML and PNG for topic, keep/remove, and unanimous under `outputs/figures/original/<UTC_TS>/`.

### Step 6: Smoke end-to-end on 50 posts (approval gate)

Run stages 1–4 on a fixed sample of **50** original posts. Confirm cache, topics, labels, and all six figure files land. **Stop and wait for explicit user approval.** Do not run the full-corpus production path or write production `RESULTS.md` here.

### Step 7: Full-corpus production run and RESULTS.md

Only after Step-6 approval: run stages 2–4 on **all** original posts (reuse embedding cache), then write `experiments/bertopic_modeling_2026_08_05/RESULTS.md` with model/embedding ids, fit params, topic counts (including noise), label model, figure paths, and artifact run directories.

## What "done" looks like

1. `experiments/bertopic_modeling_2026_08_05/src/` contains the six modules listed in Overview.
2. `bertopic` is declared only under `[project.optional-dependencies]` as the `bertopic` extra in `pyproject.toml` (not in default deps or `dev`); install with `uv sync --extra bertopic`; stages run with `PYTHONPATH=. uv run --extra bertopic python …`.
3. `outputs/embeddings/original/` holds a complete Titan cache aligned to original-text posts by `message_id`.
4. Stage 2 writes a timestamped topics run (assignments, c-TF-IDF topic info, `umap_2d.npy`, model) with no OpenAI calls.
5. Stage 3 writes LLM topic labels for non-noise topics only, linked to a specific topics run.
6. Stage 4 writes six figure files (HTML + PNG × three overlays) from one 2-D projection.
7. Smoke completes on a fixed **50-post** sample; full-corpus run is gated on explicit user approval of smoke artifacts.
8. Production fit uses **all** original posts; keep/remove and unanimous overlays do not affect clustering.
9. `RESULTS.md` records the production run parameters and artifact paths.
10. No mirror pipeline, no `export_features.py`, no changes to `shared/data/` or `shared/embeddings/bedrock.py`.
