# Step 4: Cluster feature embeddings (HDBSCAN + KMeans)

## Goal

Implement `experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py` to load Stage-2 embeddings for one label class, fit **both** HDBSCAN and KMeans, write both assignment artifacts, and save comparison scatter PNGs. **HDBSCAN is the downstream source of truth** (Step 5 labeling, Steps 6–7 artifacts that feed labels/`RESULTS.md`). KMeans assignments + PNG exist for visual comparison and reproducibility only.

## Dependency note (exact)

| Package | In `pyproject.toml`? | Decision |
|---------|----------------------|----------|
| `hdbscan` (standalone PyPI) | **No** | Do **not** add it |
| `scikit-learn>=1.8.0` | Yes — `dependency-groups.dev` | Use `sklearn.cluster.HDBSCAN` and `sklearn.cluster.KMeans` |
| `matplotlib>=3.10.9` | Yes — project `dependencies` | Use for PNG scatter plots |

**Do not change `pyproject.toml` for this step.** Offline wiring must import `from sklearn.cluster import HDBSCAN, KMeans`.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep \
  --embeddings-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/keep/<STAGE2_TS> \
  --seed 42
```

**In scope:** Stage-3 dual clustering + PNG viz only.

**Out of scope:** LLM labeling, re-embedding, train/test error-lift analysis from the July-15 reference script, labeling KMeans clusters, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/model_errors_analysis_2026_07_15/analyze/cluster.py` | `select_k_silhouette`, `KMeans` defaults (`n_init=10`, `max_iter=300`), silhouette metric (KMeans path only) |
| `/Users/mark/src/work/mirrorView-task/pyproject.toml` | Confirm sklearn in `dev`; no standalone `hdbscan`; matplotlib present |
| Stage-2 artifacts under `outputs/generated_embeddings/{keep,remove}/` | Matrix + feature_id alignment from Step 3 |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/paths.py` (or `data.py`) | `stage3_root` |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/PLAN.md` | Conceptual clustering→label intent only (do not adopt that folder layout) |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (Stage-3 CLI: dual methods, HDBSCAN downstream, PNG paths)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/clusters/{keep,remove}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/pyproject.toml` (use sklearn HDBSCAN; do not add standalone `hdbscan`)
- `/Users/mark/src/work/mirrorView-task/experiments/model_errors_analysis_2026_07_15/**`
- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`

## Contracts

### Shared input prep

1. Load all feature embeddings for one label class from one Stage-2 run directory.
2. Stack into `X` with shape `(n_features, 256)`.
3. Optional: `StandardScaler` fit on all rows of this class (document in metadata whether used). Default: **fit StandardScaler on all rows**, then run both clusterers on the scaled matrix (no PCA required for the primary path).
4. There is **no** held-out `predict` split.

### Method A — HDBSCAN (downstream source of truth)

1. Fit `sklearn.cluster.HDBSCAN` on the (scaled) matrix. Pin defaults in metadata; recommended starting point: `min_cluster_size=5`, `metric="euclidean"` (adjust only if smoke \(n\) is too small — document any override in metadata + README).
2. Write one assignment row per feature_id. Noise points (`label == -1`) **remain** as `cluster_id=-1` (do not drop). Step 5 must skip labeling noise **or** treat `-1` as a single “noise / unclustered” bucket — pick one policy, document it in metadata as `hdbscan_noise_policy`, and keep it consistent through Steps 5–7. **Preferred:** skip `cluster_id=-1` for LLM labeling; still list noise count in metadata/`RESULTS.md`.
3. Record in metadata: `n_clusters` (excluding noise), `n_noise`, params, `method="hdbscan"`.

### Method B — KMeans (comparison only)

Algorithmic reference: `experiments/model_errors_analysis_2026_07_15/analyze/cluster.py` (`select_k_silhouette`).

1. Select \(k\) by maximizing silhouette on the same matrix:

   - `k_range = range(2, min(16, n_features))`  # k from 2 through min(15, n_features-1)
   - If `n_features < 4`, set `k = 1`, write assignments, skip silhouette; record `k_selection="n_features_lt_4_forced_k1"`.
   - Else same logic as `select_k_silhouette` (`KMeans(..., random_state=seed, n_init=10, max_iter=300)`, `silhouette_score(..., metric="euclidean", sample_size=min(4000, n), random_state=seed)`).
2. Fit final `KMeans(n_clusters=selected_k, random_state=seed, n_init=10, max_iter=300)` and `fit_predict`.
3. Write KMeans assignments covering every feature_id. These are **not** fed to Step 5.

### PNG visualization (exact paths)

Project to 2D for plotting (PCA `n_components=2` on the same scaled matrix used for clustering; document in metadata). Color by cluster label (noise in gray for HDBSCAN).

Write/overwrite these **exact** class-root paths (not only under the timestamp run dir):

| Path |
|------|
| `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_hdbscan.png` |
| `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_kmeans.png` |
| `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_hdbscan.png` |
| `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_kmeans.png` |

Also copy the same two PNGs into the timestamped run directory for that class so each run is self-contained.

### Output layout (timestamped run)

Write under `stage3_root(label_class) / {run_timestamp}/`:

| File | Content |
|------|---------|
| `metadata.json` | `label_class`, `source_embeddings_run_dir`, `seed`, `scaler`, both methods’ params, `downstream_method="hdbscan"`, `hdbscan_noise_policy`, `n_features`, `embedding_dim=256`, paths to class-root PNGs |
| `assignments_hdbscan.json` **or** `.csv` | One row per feature: `feature_id`, `message_id`, `feature_name`, `feature_value`, `cluster_id` (incl. `-1` noise), plus fields for Stage 5 (`rationale` recommended) |
| `assignments_kmeans.json` **or** `.csv` | Same columns; KMeans `cluster_id` only |
| `k_selection.json` | KMeans `{k, silhouette, inertia}` rows (omit if forced k=1) |
| `cluster_sizes_hdbscan.json` | sizes excluding or including noise — document key for `-1` |
| `cluster_sizes_kmeans.json` | `{ "0": n0, ... }` |
| `cluster_hdbscan.png` | copy of class-root PNG |
| `cluster_kmeans.png` | copy of class-root PNG |

Pin CSV vs JSON in README; Step 5 must load **`assignments_hdbscan.*` only**.

Also maintain a convenience pointer file or README note so Step 5 knows the latest run dir; CLI still takes `--clusters-run-dir`.

### Determinism

Pass `--seed` through to KMeans / silhouette `random_state`. HDBSCAN itself is largely deterministic for fixed inputs; document sklearn version. Same inputs + seed → same KMeans `selected_k` and assignments.

## Exact commands

### Offline wiring

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib
from experiments.create_llm_features_2026_08_05.src import cluster_embeddings as m
assert hasattr(m, 'main') or hasattr(m, 'run_cluster_embeddings')
print('cluster wiring OK')
"
```

### Live cluster (requires Stage-2 artifacts)

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep \
  --embeddings-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/keep/STAGE2_TS \
  --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class remove \
  --embeddings-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/remove/STAGE2_TS \
  --seed 42
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Dual methods | both `assignments_hdbscan.*` and `assignments_kmeans.*` exist; every Stage-2 feature_id appears once in each | Only one method / dropped ids |
| Downstream flag | `metadata.json` has `downstream_method="hdbscan"` | Ambiguous or KMeans as default |
| PNGs | all four class-root PNG paths exist and are non-empty | Missing / wrong path |
| HDBSCAN import | `sklearn.cluster.HDBSCAN` (no standalone `hdbscan` package) | Added `hdbscan` to pyproject without need |
| Paths | under `outputs/clusters/{keep,remove}/` | Writing into embeddings tree |
| Reference isolation | no edits under `model_errors_analysis_2026_07_15/` | Diff in that experiment |
| pyproject | unchanged | Standalone `hdbscan` added unnecessarily |

## Done when

- Keep and remove embedding runs are clustered with **both** HDBSCAN and KMeans.
- Both assignment artifacts + four class-root PNGs exist.
- Step 5 can load `assignments_hdbscan.*` and sample member features by `cluster_id` (noise policy documented).
- KMeans is comparison-only; not consumed by labeling.
