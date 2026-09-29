# Step 4: Cluster the features within each category

Step 4 groups the distinct features from step 3 into clusters, one HDBSCAN run per category. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py`. Step 4 calls no model.

Out of scope are cluster names, KMeans, and any change to `shared/feature_discovery/`.

## Decisions

Reuse `resolve_hdbscan_params` and `fit_hdbscan` from `shared/feature_discovery/llm_based/cluster.py`. Do not use `run_dual_clustering`, because it expects the older embedding folder layout, it also fits KMeans, and it applies `StandardScaler`. The Titan vectors are unit length, so Euclidean distance on the raw vectors ranks pairs the same way cosine distance does, and scaling each dimension would change that.

For each category in `FEATURE_CATEGORIES`, take the matrix rows of that category's features in `feature_ids.json` order. Call `resolve_hdbscan_params(n_features, 5)` and then `fit_hdbscan(matrix, min_cluster_size, min_samples)`. With 10 or more features in a category, both values are 5. A category with fewer than 2 features gets no clusters, and the run prints a warning for it.

HDBSCAN in scikit-learn takes no random seed, and it returns the same labels for the same input order, so the row order is fixed by `feature_ids.json`. Record `SEED` (1) in `metadata.json` anyway, so the run log shows the seed from the issue.

Label `-1` is noise. Noise features get no cluster, and step 5 does not name them. The cluster key is the category, two underscores, and the cluster id padded to 3 digits, for example `pragmatics__004`.

Each cluster summary row sums the step 3 counts of its members. `n_batches` is the number of distinct batch ids in the union of the members' `batch_ids`, so a batch that produced two members counts once.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/workspace/shared/feature_discovery/llm_based/cluster.py` | `resolve_hdbscan_params`, `fit_hdbscan` |
| `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/dedupe.py` | Feature columns |

## Files allowed to change

All paths are under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `src/step4_cluster_records/__init__.py`, `cluster.py`, and `run.py`
- Edit `SETUP.md` to add the step 4 command, and edit `RESULTS.md` under `## Step 4: clusters`

## Files forbidden to change

- `/workspace/shared/**`
- Everything under `src/step1_setup/`, `src/step2_mine_candidate_features/`, and `src/step3_embed_features/`

## Contracts

Add to `shared/constants.py`:

```text
HDBSCAN_MIN_CLUSTER_SIZE = 5
HDBSCAN_NOISE_LABEL = -1
CLUSTER_ID_WIDTH = 3
ASSIGNMENTS_KEY = "step4_cluster_records/assignments.parquet"
CLUSTER_SIZES_KEY = "step4_cluster_records/cluster_sizes.parquet"
CLUSTER_METADATA_KEY = "step4_cluster_records/metadata.json"
```

`src/step4_cluster_records/cluster.py`:

```text
format_cluster_key(category: str, cluster_id: int) -> str

cluster_category(matrix: np.ndarray, min_cluster_size: int) -> tuple[np.ndarray, dict]
  resolve_hdbscan_params then fit_hdbscan. Return the labels and the params dict.
  Raise ValueError when matrix has fewer than 2 rows.

cluster_all_categories(features: pd.DataFrame, matrix: np.ndarray,
                       feature_ids: list[str]) -> tuple[pd.DataFrame, dict]
  Return assignments with columns feature_id, category, cluster_id, and cluster_key, where
  cluster_key is None for noise, and a per-category params dict.
  Raise ValueError when feature_ids does not match features.feature_id as a set.

summarize_clusters(assignments: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame
  Non-noise clusters only. Columns cluster_key, category, n_features, n_occurrences,
  n_batches, n_kept_side, n_removed_side, sorted by cluster_key.
```

`src/step4_cluster_records/run.py` has `main()`. It downloads the three step 3 files, clusters, and writes and uploads `ASSIGNMENTS_KEY`, `CLUSTER_SIZES_KEY`, and `CLUSTER_METADATA_KEY`. The metadata holds `SEED`, `HDBSCAN_MIN_CLUSTER_SIZE`, the per-category params, the number of clusters, and the noise count. It prints one line per category and one total line.

## Commands

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
```

The run prints one line per category and a total line, where `K` is the number of clusters and `Z` is the number of noise features:

```text
category=lexical n_features=... clusters=... noise=...
total_clusters=K total_noise=Z
```

Write a table of features, clusters, and noise per category under `## Step 4: clusters` in `RESULTS.md`.

## Pass

`K` is at least 1, the number of clustered features plus `Z` equals the step 3 distinct count, and the three files are on S3.

## Fail

The step fails when the assignments miss a feature id, when a cluster key mixes categories, or when `StandardScaler` or KMeans is applied.
