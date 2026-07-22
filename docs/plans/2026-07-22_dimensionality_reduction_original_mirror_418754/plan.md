# Plan: PCA/LDA of original vs mirrored Titan embeddings

**Plan assets:** `docs/plans/2026-07-22_dimensionality_reduction_original_mirror_418754/`  
**Target experiment:** `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/`  
**Reference experiment:** `experiments/model_errors_analysis_2026_07_15/` (especially `analyze/embed_2d.py`)  
**Date:** 2026-07-22  
**UI screenshots:** skipped — no `ui/` / frontend changes (Phase 4 N/A)

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- Operational changes: inventory `docs/runbooks/`; list updates and new runbooks from the runbook template
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

---

## Overview

Build a new offline experiment that visualizes Titan text embeddings of **original** vs **mirrored** post texts with the same leakage-safe PCA/LDA pattern used in `experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py`, but with the supervised target and plot colors switched from Qwen right/wrong to **original vs mirrored**. Each study `post_id` contributes two 256-d vectors (`original_text`, `mirror_text`) stacked into one long matrix with binary label `is_mirrored`; the train/test split is at **post_id** level so a post’s original and mirror never cross the split. Embeddings come from the existing local Titan `.npy` cache (no Bedrock calls). Outputs: `pca_original_vs_mirrored.png`, `lda_original_vs_mirrored.png`, coords CSV, and a reduction summary with variance and separation diagnostics.

---

## Happy Flow

1. **Load study posts (one row per `post_id`)** via `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` → `Dataloader().load_training_dataframe()` with columns `post_id`, `original_text`, `mirror_text`, `keep_remove_label` (from `keep_remove_results_2026_06_23.csv`). Expected ≈ **8,791** unique posts (same cohort as model-errors analysis).

2. **Resolve Titan cache** (prefer worktree, then optional Documents backup — same pattern as `experiments/model_errors_analysis_2026_07_15/analyze/build_table.py::resolve_embedding_cache_dir`):
   - **Primary (happy path):** `experiments/predict_keep_remove_2026_07_01/embedding_cache/` (worktree)
   - **Optional backup:** `/Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache/`  
   **Cache status (2026-07-22):** worktree cache populated by local filesystem copy from Documents (`rsync -a`); **~17,370** `embeddings/*.npy` files under the worktree path. Do **not** load from S3 / DynamoDB / Bedrock. Documents remains an optional fallback only — not a hard dependency for the happy path. Script must still fail loud if neither path is populated.

3. **Hash and load both roles** using `lib.aws.embedding_identity.embedding_identity_sha256` with `amazon.titan-embed-text-v2:0`, dims=256, `normalize=True`. Roles from `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`:
   - `TEXT_ROLE_ORIGINAL = "original_text"`
   - `TEXT_ROLE_MIRROR = "mirror_text"`  
   Pattern reference for dual-role loading: `experiments/predict_keep_remove_2026_07_01/reports/generate/cosine_histogram.py`.

4. **Build long analysis matrix** in `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py`:
   - Emit **2 rows per `post_id`** (order: original then mirror, or stable sort by `(post_id, is_mirrored)`).
   - Columns in meta: `post_id`, `text_role`, `is_mirrored` (0=original, 1=mirrored), `label` (keep/remove from training table; optional context only).
   - Matrix `X_original_and_mirror.npy` shape `(2N, 256)` row-aligned with meta.
   - Fail if any original or mirror `.npy` is missing (no DynamoDB/S3/Bedrock fallback in v1).

5. **Split at post level** in `analyze/split.py` (adapt `experiments/model_errors_analysis_2026_07_15/analyze/split.py`):
   - Unit of split = unique `post_id` (not row).
   - `train_test_split(..., test_size=0.2, random_state=42, stratify=keep_remove_label)`.
   - Expand: every train/test `post_id` contributes **both** original and mirror rows to that split.
   - Assert: train∩test post_ids = ∅; no post has rows in both splits; each post contributes exactly 2 rows.

6. **Fit reductions on train rows only** in `analyze/embed_2d.py` (adapt `experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py`):
   - `StandardScaler.fit(X[train_rows])` → transform all
   - `PCA(n_components=2).fit(Xs[train_rows])` → transform all
   - `LDA(n_components=1).fit(Xs[train_rows], y=is_mirrored[train_rows])` → transform all
   - Residual PC1 orthogonal to LDA direction (same residual-PCA trick as reference)
   - Optional viz-only 2D logistic on PCA coords predicting `is_mirrored` (train-fit; contour on both panels)

7. **Plot and write artifacts** under `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/`:
   - `pca_original_vs_mirrored.png` — Train|Test panels; color original=`#2A9D8F` circles, mirrored=`#E76F51` crosses (swap legend text from right/wrong)
   - `lda_original_vs_mirrored.png` — LD1 vs residual PC1; same colors; axis label `LD1 (fit on train; target=is_mirrored)`
   - `embeddings_2d.csv` — `post_id,text_role,is_mirrored,pc1,pc2,ld1,lda_orth_pc1,split,label`
   - `reduction_summary.json`, `pca_variance_explained.json`, `split_ids.json`, `progress_updates*.md`

8. **Interpret on test panel / test metrics** (not train): PCA variance cumsum, LDA class-mean separation / Cohen-d / midpoint accuracy for `is_mirrored`. Strong separation is the scientific expectation if mirrors systematically shift embedding geometry; heavy overlap would be a surprising negative result.

---

## Manual Verification

Run all commands from repo root `/Users/mark/src/work/mirrorView-task` unless noted.

### Preconditions checklist

- [ ] Titan cache reachable at worktree path (primary):  
  `ls experiments/predict_keep_remove_2026_07_01/embedding_cache/embeddings | wc -l`  
  **Expected:** `17370` (or similar large count > 10000).  
  Optional backup check (not required for happy path):  
  `ls /Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache/embeddings | wc -l`
- [ ] Training CSV present:  
  `test -f experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv && echo OK`  
  **Expected:** `OK`.
- [ ] No Bedrock / AWS required for the happy path.

### Unit / contract tests

- [ ] Run experiment tests (after they land under the new experiment):  
  ```bash
  PYTHONPATH=. uv run pytest experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/ -q
  ```  
  **Expected:** all tests pass (pair-leakage invariant, matrix shape `2N×256`, LDA target values `{0,1}`, split post_id disjointness).

### End-to-end pipeline

- [ ] Build long table:  
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py
  ```  
  **Expected stdout:** reports `n_posts≈8791`, `n_rows≈17582`, `cache_misses=0`, writes:
  - `.../outputs/analysis/analysis_meta.csv`
  - `.../outputs/analysis/X_original_and_mirror.npy`
  - `.../outputs/analysis/analysis_table.parquet` (optional but preferred)
  - `.../outputs/analysis/analysis_table_meta.json`

- [ ] Shared split:  
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split.py
  ```  
  **Expected:** `split_ids.json` with `n_train`≈7032 posts, `n_test`≈1759 posts; row counts after expand ≈ `2×` those; asserts printed for disjointness.

- [ ] PCA/LDA viz:  
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/embed_2d.py
  ```  
  **Expected files:**
  - `outputs/analysis/pca_original_vs_mirrored.png`
  - `outputs/analysis/lda_original_vs_mirrored.png`
  - `outputs/analysis/embeddings_2d.csv`
  - `outputs/analysis/reduction_summary.json`
  - `outputs/analysis/pca_variance_explained.json`

### Visual / numeric sanity

- [ ] Open both PNGs: Train and Test panels present; legend shows **original** and **mirrored** (not right/wrong); two colors/markers distinguishable.
- [ ] Read variance:  
  ```bash
  PYTHONPATH=. uv run python -c "import json; p='experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/pca_variance_explained.json'; print(json.load(open(p)))"
  ```  
  **Expected:** two PC ratios summing to a small but positive fraction (order ~few percent is normal for Titan 256-d; record exact values in README/RESULTS).
- [ ] Read LDA separation from `reduction_summary.json`: test-set Cohen-d and/or midpoint accuracy for `is_mirrored` present and finite.  
  **Interpretation note:** higher Cohen-d than the prior right/wrong analysis (~0.33) would indicate original/mirror is a stronger linear axis than Qwen error — do not fail the pipeline solely because separation is weak; record the result.
- [ ] Leakage check:  
  ```bash
  PYTHONPATH=. uv run python -c "
  import json
  s=json.load(open('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/split_ids.json'))
  assert set(s['train_post_ids']) & set(s['test_post_ids']) == set()
  print('ok', s['n_train'], s['n_test'])
  "
  ```  
  **Expected:** `ok <n_train> <n_test>`.

### Negative checks

- [ ] With empty/missing cache, `build_table.py` exits non-zero with a clear path error (no silent AWS call).
- [ ] `embed_2d.py` without `split_ids.json` exits non-zero telling the operator to run `split.py` first.

---

## Alternative approaches

| Option | Description | Decision |
|--------|-------------|----------|
| **A. Long stacked matrix + `is_mirrored` LDA (chosen)** | 2N rows; color and LDA target = original vs mirrored; split on `post_id` | **Chosen** — matches the user’s ask; reuses `embed_2d.py` almost 1:1; scientifically answers “are original and mirror linearly separable in Titan space?” |
| **B. Color-only on existing `only_original` matrix** | Keep one row per post; recolor somehow | **Rejected** — there is no mirrored point in `X_only_original.npy`; coloring would be meaningless |
| **C. Wide concat `[orig‖mirror]` then PCA** | One row per post, 512-d | **Rejected for primary viz** — loses “two clouds” story; useful as a future ablation, not this request |
| **D. Difference vectors `orig−mirror` only** | PCA of differences | **Out of scope** — different question (within-pair deltas); already related to `difference_embedding` training ablation |
| **E. Import/call model-errors scripts in place** | Monkey-patch colors in old experiment | **Rejected** — different scientific target; would pollute Qwen-error artifacts; new experiment dir keeps results clean |
| **F. DynamoDB→S3 fallback on cache miss** | Like some training paths | **Deferred** — cosine_histogram / model-errors happy path is local-only; keep v1 fail-loud offline |

---

## Serial Coordination Spine

1. **S0 — Scaffold + contract freeze (coordinator only)**  
   Create experiment directory tree, write `analyze/paths.py`, write `spec.md` (or freeze block in this plan’s contracts into `spec.md`), empty `outputs/analysis/.gitkeep`. No parallel work starts until contracts below are merged.

2. **S1 — Land Parallel Task Packets T1–T3** (after freeze): build_table, tests, README (docs can merge anytime after freeze).

3. **S2 — Land T4 (`split.py`)** after T1’s real meta schema is on disk *or* after T2’s fixture-based verification proves the split contract (prefer: implement T4 against freeze; integration uses T1 outputs).

4. **S3 — Land T5 (`embed_2d.py`)** after split contract is frozen (can develop in parallel with T1 using fixtures; integration requires T1+T4 artifacts).

5. **S4 — Integration run** on real worktree Titan cache (`experiments/predict_keep_remove_2026_07_01/embedding_cache/`); fill `RESULTS.md` with observed metrics and plot paths.

6. **S5 — Final Verification** (checklist below).

---

## Interface or Contract Freeze

Lock these before any parallel implementation. Do not change without coordinator amendment.

### Paths (`analyze/paths.py`)

| Constant | Value |
|----------|-------|
| `EXPERIMENT_ROOT` | `Path(__file__).resolve().parents[1]` → `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22` |
| `OUTPUTS_DIR` | `EXPERIMENT_ROOT / "outputs"` |
| `ANALYSIS_DIR` | `OUTPUTS_DIR / "analysis"` |
| `ANALYSIS_META_PATH` | `ANALYSIS_DIR / "analysis_meta.csv"` |
| `ANALYSIS_TABLE_PATH` | `ANALYSIS_DIR / "analysis_table.parquet"` |
| `EMBEDDING_MATRIX_PATH` | `ANALYSIS_DIR / "X_original_and_mirror.npy"` |
| `SPLIT_IDS_PATH` | `ANALYSIS_DIR / "split_ids.json"` |
| `PCA_PLOT_PATH` | `ANALYSIS_DIR / "pca_original_vs_mirrored.png"` |
| `LDA_PLOT_PATH` | `ANALYSIS_DIR / "lda_original_vs_mirrored.png"` |
| `EMBEDDINGS_2D_PATH` | `ANALYSIS_DIR / "embeddings_2d.csv"` |
| `REDUCTION_SUMMARY_PATH` | `ANALYSIS_DIR / "reduction_summary.json"` |
| `PCA_VARIANCE_PATH` | `ANALYSIS_DIR / "pca_variance_explained.json"` |
| `WORKTREE_EMBEDDING_CACHE` | `REPO_ROOT / "experiments/predict_keep_remove_2026_07_01/embedding_cache"` — **primary resolve target** (populated locally 2026-07-22; no S3) |
| `MAIN_REPO_EMBEDDING_CACHE` | `/Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache` — **optional backup only** after successful worktree copy |
| `FEATURE_SET` | `"original_and_mirror_long"` |
| `EMBEDDING_DIM` | `256` |
| `SPLIT_SEED` | `42` |
| `TRAIN_SPLIT` | `0.8` |
| `STRATIFY_ON` | `"label"` (post-level keep/remove; **not** `is_mirrored`) |
| `LDA_TARGET` | `"is_mirrored"` |

### Long-table schema (`analysis_meta.csv` / parquet scalars)

| Column | Type | Invariant |
|--------|------|-----------|
| `post_id` | str | Exactly **2** rows per post_id |
| `text_role` | str | ∈ `{"original_text", "mirror_text"}` |
| `is_mirrored` | int | `0` iff `text_role=="original_text"`; `1` iff `text_role=="mirror_text"` |
| `label` | int | keep/remove from training dataframe (0/1); identical on both rows of a post |

### Matrix

- `X_original_and_mirror.npy`: `float64`, shape `(len(meta), 256)`, row `i` matches meta row `i`.
- No Qwen / `is_correct` / `is_error` columns in this experiment.

### `split_ids.json`

```json
{
  "seed": 42,
  "train_split": 0.8,
  "stratify_on": "label",
  "feature_set": "original_and_mirror_long",
  "lda_target": "is_mirrored",
  "n_posts_total": "<int>",
  "n_train": "<int posts>",
  "n_test": "<int posts>",
  "n_rows_train": "<int = 2 * n_train>",
  "n_rows_test": "<int = 2 * n_test>",
  "train_post_ids": ["..."],
  "test_post_ids": ["..."]
}
```

**Invariants:** `set(train_post_ids) ∩ set(test_post_ids) = ∅`; union equals all meta post_ids; after expand, every post contributes both roles to exactly one split.

### Plot / color contract

| Class | `is_mirrored` | Color | Marker |
|-------|---------------|-------|--------|
| original | 0 | `#2A9D8F` | `o` |
| mirrored | 1 | `#E76F51` | `x` |

Titles must say **original vs mirrored** and **Titan original+mirror long matrix** — never “Qwen” / “right vs wrong”.

### Forbidden in v1

- Calling Bedrock embed, Converse, or `api_baselines/*/train.py`
- Re-using `model_errors_analysis_2026_07_15/outputs/` as write targets
- Splitting at row level (would leak pairs)
- Stratifying the post split on `is_mirrored` (undefined / constant at post level)

### Open choice locked for v1 (see Discussion)

- Stratify post split on **`label`** (keep/remove). Alternative (no stratify) is deferred unless coordinator amends.

---

## Parallel Task Packets

### T1 — `build_table.py` (long orig+mirror matrix)

- **Task ID:** `T1`
- **One-sentence objective:** Load PKR training posts and both Titan role vectors from the local `.npy` cache into a long `(2N, 256)` matrix and aligned meta CSV/parquet.
- **Why this task is parallelizable:** Owns only build_table + its direct helpers; does not touch split or viz files; contracts are frozen in S0.
- **Exact files to inspect:**
  - `experiments/model_errors_analysis_2026_07_15/analyze/build_table.py`
  - `experiments/model_errors_analysis_2026_07_15/analyze/paths.py`
  - `experiments/predict_keep_remove_2026_07_01/reports/generate/cosine_histogram.py`
  - `experiments/predict_keep_remove_2026_07_01/data/dataloader.py`
  - `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` (`TEXT_ROLE_*`)
  - `lib/aws/embedding_identity.py`
- **Exact files allowed to change:**
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py` (create)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/__init__.py` (create if missing)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/.gitkeep` (optional)
- **Exact files forbidden to change:**
  - Anything under `experiments/model_errors_analysis_2026_07_15/`
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/paths.py` (owned by S0; read-only here)
  - `analyze/split.py`, `analyze/embed_2d.py`, `README.md`, `tests/**`
- **Preconditions:** S0 complete (`paths.py` exists with frozen constants).
- **Dependency tasks:** S0
- **Required contracts and invariants:** Long-table schema; `FEATURE_SET`; fail-loud on cache miss; no AWS; exactly 2 rows per `post_id`; `is_mirrored` ↔ `text_role` consistency.
- **Step-by-step implementation instructions:**
  1. Copy structure from `model_errors_analysis_2026_07_15/analyze/build_table.py` into the new `build_table.py`.
  2. Replace label loading: call `Dataloader().load_training_dataframe()`; rename `keep_remove_label` → `label` as int if needed (match PKR conventions used elsewhere: keep=0/remove=1 or whatever dataloader already exposes — inspect and document in script docstring).
  3. Implement `load_original_and_mirror_from_local_cache(df, cache_dir)` that hashes both `original_text` and `mirror_text`, loads `.npy`, returns lookup keyed by `(post_id, text_role)`.
  4. Stack into long meta + `X` with row order stable: sort by `(post_id, is_mirrored)`.
  5. Write `analysis_meta.csv`, `X_original_and_mirror.npy`, `analysis_table.parquet` (scalars + `embedding` list column), `analysis_table_meta.json` with `feature_set`, `cache_dir`, `n_posts`, `n_rows`, `embedding_dim`.
  6. Print hit/miss stats; raise `FileNotFoundError` if any miss.
- **Exact verification commands:**
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py
  PYTHONPATH=. uv run python -c "
  import numpy as np, pandas as pd
  meta=pd.read_csv('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_meta.csv')
  X=np.load('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/X_original_and_mirror.npy')
  assert len(meta)==len(X)==2*meta['post_id'].nunique()
  assert set(meta['is_mirrored'])=={0,1}
  assert X.shape[1]==256
  print('ok', X.shape, meta['post_id'].nunique())
  "
  ```
- **Expected outputs from verification:** `ok (17582, 256) 8791` (exact N may vary slightly if dataloader filters; assert `len(meta)==2*nunique` always).
- **Done-when checklist:**
  - [ ] Artifacts written under new experiment `outputs/analysis/`
  - [ ] No writes under model-errors experiment
  - [ ] Cache miss raises
  - [ ] Docstring documents run command from repo root
- **Coordinator review checklist:**
  - [ ] Row order deterministic
  - [ ] Role strings exactly `original_text` / `mirror_text`
  - [ ] Does not import Qwen prediction paths

---

### T2 — Pair-leakage and schema unit tests

- **Task ID:** `T2`
- **One-sentence objective:** Add pytest coverage that proves post-level split cannot put a post’s original and mirror on opposite sides, and that long-matrix schema invariants hold on synthetic fixtures.
- **Why this task is parallelizable:** Owns only `tests/`; can use synthetic numpy/pandas fixtures without the real Titan cache.
- **Exact files to inspect:**
  - Frozen contracts in this plan / `spec.md`
  - `experiments/model_errors_analysis_2026_07_15/analyze/split.py` (reference assertions)
  - Existing pytest layout under `experiments/fetch_reddit_pushshift_dump_2026_06_15/tests/` (style only)
- **Exact files allowed to change:**
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/test_split_pair_leakage.py` (create)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/test_build_table_schema.py` (create)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/__init__.py` (create if needed)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split.py` — **only if** extracting a pure function `expand_post_split_to_row_masks(meta, train_post_ids, test_post_ids)` for testability; if that file is not yet created, put the helper in `analyze/split_lib.py` instead and allow only that new file
- **Exact files forbidden to change:**
  - `analyze/build_table.py`, `analyze/embed_2d.py`, `analyze/paths.py`, `README.md`
  - Any file under `experiments/model_errors_analysis_2026_07_15/`
- **Preconditions:** S0 (`paths.py` + contract freeze). Prefer implementing against a small pure helper rather than importing unfinished scripts.
- **Dependency tasks:** S0 (and T4 if testing real `split.py` functions — otherwise fixture-only)
- **Required contracts and invariants:** Post-level disjointness; 2 rows/post; `is_mirrored` encoding; expand masks yield `n_rows_train == 2 * n_train_posts`.
- **Step-by-step implementation instructions:**
  1. Create synthetic meta: 10 posts × 2 roles, labels balanced.
  2. Test that a deliberately bad row-level split is detected by an assertion helper (document the helper API in the test module docstring).
  3. Test that post-level split + expand never assigns the same `post_id` to both masks.
  4. Test `is_mirrored` / `text_role` consistency checker.
  5. Do not require Documents cache.
- **Exact verification commands:**
  ```bash
  PYTHONPATH=. uv run pytest experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/ -q
  ```
- **Expected outputs from verification:** all tests passed; exit code 0.
- **Done-when checklist:**
  - [ ] At least one test fails if pair leakage is introduced
  - [ ] Tests run without embedding cache
- **Coordinator review checklist:**
  - [ ] No network/AWS
  - [ ] Assertions match frozen contract field names

---

### T3 — Experiment README + RESULTS stub

- **Task ID:** `T3`
- **One-sentence objective:** Document purpose, cache prerequisite, exact run commands, and output artifact names for the new experiment.
- **Why this task is parallelizable:** Docs-only; exclusive ownership of README/RESULTS stubs.
- **Exact files to inspect:**
  - `experiments/model_errors_analysis_2026_07_15/README.md`
  - This plan’s Happy Flow + Manual Verification
- **Exact files allowed to change:**
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/README.md` (create)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/RESULTS.md` (create stub with TBD metrics)
- **Exact files forbidden to change:**
  - All `analyze/*.py`, `tests/**`, `docs/runbooks/**`
- **Preconditions:** S0
- **Dependency tasks:** S0
- **Required contracts and invariants:** Commands match frozen paths; state **no Bedrock / no S3**; document worktree cache as primary prerequisite and Documents path as optional backup only.
- **Step-by-step implementation instructions:**
  1. Mirror model-errors README structure but replace Qwen/right-wrong with original/mirrored.
  2. Include the three-command pipeline: `build_table.py` → `split.py` → `embed_2d.py`.
  3. List output PNG/CSV/JSON names from the contract freeze.
  4. Leave numeric RESULTS placeholders (`PC1+PC2=…`, `LDA Cohen-d test=…`) for S4 fill-in.
- **Exact verification commands:**
  ```bash
  test -f experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/README.md && grep -n 'embed_2d.py' experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/README.md
  ```
- **Expected outputs from verification:** file exists; grep finds the viz command.
- **Done-when checklist:**
  - [ ] Cache prerequisite documented
  - [ ] No instruction to call Bedrock
- **Coordinator review checklist:**
  - [ ] Paths match `paths.py` constants
  - [ ] Does not tell user to take screenshots

---

### T4 — `split.py` (post-level, pair-safe)

- **Task ID:** `T4`
- **One-sentence objective:** Write the single shared post-level 80/20 split stratified on `label`, expand to both text roles, and refuse overlapping post_ids.
- **Why this task is parallelizable:** Exclusive ownership of `split.py`; can be developed against frozen schema + synthetic meta CSV if T1 not ready (integration later).
- **Exact files to inspect:**
  - `experiments/model_errors_analysis_2026_07_15/analyze/split.py`
  - Frozen `split_ids.json` schema above
- **Exact files allowed to change:**
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split.py` (create)
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split_lib.py` (create only if T2 requested a shared helper and it does not yet exist)
- **Exact files forbidden to change:**
  - `build_table.py`, `embed_2d.py`, `paths.py`, `README.md`, `tests/**` (unless coordinator assigns helper ownership—default: T2 owns tests)
- **Preconditions:** S0; for real-data run, T1 artifacts present.
- **Dependency tasks:** S0; integration-depends on T1
- **Required contracts and invariants:** Stratify on post-level `label`; seed 42; expand both roles; write `split_ids.json` + `analysis_with_split.csv` (long rows with `split` column).
- **Step-by-step implementation instructions:**
  1. Adapt model-errors `split.py`.
  2. Collapse meta to one row per `post_id` for `train_test_split` (take `label` from either role — must be identical).
  3. Expand IDs back to row masks.
  4. Assert `n_rows_train == 2 * n_train`, etc.
  5. Do **not** call `train_test_split` from any other module.
- **Exact verification commands:**
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split.py
  PYTHONPATH=. uv run python -c "
  import json, pandas as pd
  s=json.load(open('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/split_ids.json'))
  meta=pd.read_csv('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_meta.csv')
  assert set(s['train_post_ids']) & set(s['test_post_ids']) == set()
  assert s['n_rows_train'] == 2 * s['n_train']
  print('ok', s['n_train'], s['n_test'], s['n_rows_train'], s['n_rows_test'])
  "
  ```
- **Expected outputs from verification:** `ok` with `n_rows_*` exactly double post counts.
- **Done-when checklist:**
  - [ ] Progress markdown appended
  - [ ] Refuses duplicate post_ids across splits
- **Coordinator review checklist:**
  - [ ] Stratify column is `label`, not `is_mirrored`
  - [ ] Feature set string matches freeze

---

### T5 — `embed_2d.py` (PCA/LDA original vs mirrored)

- **Task ID:** `T5`
- **One-sentence objective:** Fit leakage-safe StandardScaler/PCA/LDA on train rows with target `is_mirrored` and write original-vs-mirrored scatter plots plus summary JSON/CSV.
- **Why this task is parallelizable:** Exclusive ownership of `embed_2d.py`; can be unit-checked with synthetic X/meta/split fixtures before real integration.
- **Exact files to inspect:**
  - `experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py` (entire file; reuse `fit_reductions`, `transform_all`, plot layout)
  - Frozen color/title/output contracts
- **Exact files allowed to change:**
  - `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/embed_2d.py` (create)
- **Exact files forbidden to change:**
  - `build_table.py`, `split.py`, `paths.py`, `README.md`, `tests/**`
  - Entire `experiments/model_errors_analysis_2026_07_15/` tree
- **Preconditions:** S0; integration needs T1+T4 artifacts.
- **Dependency tasks:** S0; integration-depends on T1, T4
- **Required contracts and invariants:** Fit on train only; LDA `y=is_mirrored`; load split — never re-split; plot colors/markers per freeze; write exact PNG filenames.
- **Step-by-step implementation instructions:**
  1. Copy `embed_2d.py` from model-errors into the new experiment.
  2. Change `load_inputs` to allow **duplicate** `post_id` (exactly 2 each); build train/test masks via `post_id ∈ split_*` (both roles included).
  3. Replace `y_error` with `y_mirrored = meta["is_mirrored"]`.
  4. Replace plot loops: original vs mirrored legend/titles/filenames.
  5. Update CSV columns per freeze; drop `is_correct`/`is_error`.
  6. Keep residual-PCA second axis and optional 2D logistic predicting `is_mirrored`.
  7. Write `reduction_summary.json` including test Cohen-d / midpoint-acc diagnostics analogous to the reference script’s LDA diagnostics.
- **Exact verification commands:**
  ```bash
  PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/embed_2d.py
  ls -la experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/pca_original_vs_mirrored.png \
         experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/lda_original_vs_mirrored.png
  PYTHONPATH=. uv run python -c "
  import json
  s=json.load(open('experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/reduction_summary.json'))
  assert 'pca_explained_variance_ratio' in s or 'pca' in s
  print('ok', list(s)[:8])
  "
  ```
- **Expected outputs from verification:** both PNGs exist; summary JSON loads.
- **Done-when checklist:**
  - [ ] No “right vs wrong” / “Qwen” strings in plot titles
  - [ ] Train-only fit preserved
  - [ ] Refuses missing `split_ids.json`
- **Coordinator review checklist:**
  - [ ] Diff against reference `embed_2d.py` shows intentional renames only + duplicate-`post_id` allowance
  - [ ] Output paths match `paths.py`

---

## Integration Order

1. Merge **S0** (`paths.py`, dir scaffold, `spec.md` contract copy).
2. Merge **T1**, **T2**, **T3** in any order (parallel).
3. Merge **T4** (`split.py`); run against T1 artifacts.
4. Merge **T5** (`embed_2d.py`); run against T1+T4 artifacts.
5. Coordinator **S4**: fill `RESULTS.md` with real PC variance, LDA Cohen-d, and embed PNGs (or links/paths).
6. Run **Final Verification**.

Do not merge T5 before the split contract is stable. Do not let T1 and T5 both edit `paths.py`.

---

## Final Verification

- [ ] `PYTHONPATH=. uv run pytest experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/tests/ -q` passes.
- [ ] Full pipeline from repo root succeeds without AWS credentials.
- [ ] `X_original_and_mirror.npy.shape[0] == 2 * n_posts` and equals `len(analysis_meta.csv)`.
- [ ] `split_ids.json` post-level disjoint; row counts double post counts.
- [ ] PNGs exist with original/mirrored legend; Train|Test panels.
- [ ] `reduction_summary.json` records PCA variance ratios and LDA test separation metrics.
- [ ] No modifications under `experiments/model_errors_analysis_2026_07_15/outputs/` from this work.
- [ ] README documents the worktree cache path (primary) and optional Documents fallback, plus the three-step command sequence.
- [ ] `RESULTS.md` filled with observed numbers (not TBD).

---

## Update Runbooks

**Runbook root:** `docs/runbooks/` — exists

### Existing runbooks

| Runbook | Status | Sections / changes needed | Why |
|---------|--------|-----------------------------|-----|
| `docs/runbooks/README.md` | no change | — | Index only; no new ops surface required in runbooks |
| `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md` | no change | — | No deploy / Lambda / S3 static-site changes |
| `docs/runbooks/CODING_GUIDES.md` | no change | — | No coding-guide policy change |
| `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md` | review recommended | Optional: after implementation, skim “original_text / mirrored_text” vocabulary vs ML `mirror_text` naming — **no edit required for this experiment** | Stimuli catalog naming differs from Titan ML column `mirror_text`; conceptual only |
| `docs/runbooks/MANUAL_TESTING.md` | no change | — | Web experiment manual testing; unrelated |
| `docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` | no change | — | Data collection ops unchanged |
| `docs/runbooks/WHAT_IS_MIRRORVIEW.md` | review recommended | No edit required; mirrors concept already documented | Background for reviewers; not an ops procedure for this analysis |

### New runbooks to create

None. Embedding PCA/LDA ops historically live in experiment READMEs (`experiments/model_errors_analysis_2026_07_15/README.md`, `experiments/predict_keep_remove_2026_07_01/embeddings/README.md`), not under `docs/runbooks/`. This plan documents the repeatable procedure in the new experiment `README.md` (T3).

### No runbook impact

None of the “when required” triggers apply beyond optional vocabulary review: this change is limited to a new offline analysis experiment under `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/` and does not alter deploy, env/auth, service boundaries, failure recovery, or operator procedures documented in `docs/runbooks/`. Verification steps for researchers belong in the experiment README / this plan’s Manual Verification.

---

## UI screenshots (Phase 4)

**Skipped.** This plan does not change anything under `ui/`, `public/`, or other participant-facing frontend paths. No before/after screenshots.

---

## Discussion notes for the user (design choices / risks)

These are locked to recommended defaults in the Contract Freeze for implementability, but worth confirming before coding:

1. **LDA / color target = `is_mirrored`** (not keep/remove, not Qwen error). Confirm this is the scientific question.
2. **Post-level split + stratify on keep/remove `label`.** Alternative: unstratified random post split. Stratify-on-`is_mirrored` is invalid at post level.
3. **Long stack (2N×256)** vs wide concat — long stack chosen for two-cloud viz.
4. **Cache dependency:** Titan `embedding_cache/` was copied into this worktree from Documents on **2026-07-22** (`rsync -a`; local filesystem only — do not load from S3). Happy path uses the worktree cache; Documents is an optional backup. v1 still fails loud if missing; still no S3 / DynamoDB / Bedrock fallback.
5. **Expected strong separation?** Original and mirror texts are paraphrases with opposite stance; Titan may still place them nearby (high cosine — see existing cosine histogram). Weak LDA separation is a valid empirical outcome, not a pipeline failure.
6. **YAGNI:** no clustering, no linear separator branch, no Qwen overlay, no difference-vector ablation in v1.

---

## Phase 5 checklist (plan author)

- [x] ai_tools root resolved: `/Users/mark/Documents/projects/ai_tools/`; `PLANNING_RULES.md` read
- [x] Remember block at top
- [x] All 11 required sections present (Overview, Happy Flow, Manual Verification, Alternative approaches, Specificity via paths/commands, Serial Coordination Spine, Interface/Contract Freeze, Parallel Task Packets, Integration Order, Final Verification, Update Runbooks)
- [x] Manual Verification has exact commands and expected outcomes
- [x] Update Runbooks complete (inventory + classification + no-impact justified)
- [x] Parallel delegation complete (5 packets with all required fields)
- [x] No UI → Phase 4 skipped with reason
- [x] Maximizes safe parallelism (T1∥T2∥T3 after freeze; T4/T5 exclusive files)
- [x] Plan assets path: `docs/plans/2026-07-22_dimensionality_reduction_original_mirror_418754/`
