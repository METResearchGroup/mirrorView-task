# Step 4: Cluster the features in one run

Step 4 groups every distinct feature from step 3 into clusters, in one HDBSCAN run across all mining categories. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py`. Step 4 calls no model. From this step on, the category is only the prefix of `feature_id`. The clustering, the cluster names, and the page do not group by category.

Out of scope are cluster names, KMeans, and any change to `shared/feature_discovery/`.

## Decisions

Reuse `resolve_hdbscan_params` and `fit_hdbscan` from `shared/feature_discovery/llm_based/cluster.py`. Do not use `run_dual_clustering`, because it expects the older embedding folder layout, it also fits KMeans, and it applies `StandardScaler`. The Titan vectors are unit length, so Euclidean distance on the raw vectors ranks pairs the same way cosine distance does, and scaling each dimension would change that.

Take the full embedding matrix in `feature_ids.json` order. Call `resolve_hdbscan_params(n_features, 5)` and then `fit_hdbscan(matrix, min_cluster_size, min_samples)`. With 10 or more features, both values are 5. Fewer than 2 features raises `ValueError`.

HDBSCAN in scikit-learn takes no random seed, and it returns the same labels for the same input order, so the row order is fixed by `feature_ids.json`. Record `SEED` (1) in `metadata.json` anyway, so the run log shows the seed from the issue.

Label `-1` is noise. Noise features get no cluster, and step 5 does not name them. The cluster key is `cluster_` plus the cluster id padded to 3 digits, for example `cluster_004`. A cluster may contain features from more than one mining category.

Each cluster summary row sums the step 3 counts of its members. `n_batches` is the number of distinct batch ids in the union of the members' `batch_ids`, so a batch that produced two members counts once.

## Files to inspect

| Path | Why |
|------|-----|
| `docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `shared/feature_discovery/llm_based/cluster.py` | `resolve_hdbscan_params`, `fit_hdbscan` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/dedupe.py` | Feature columns |

## Files allowed to change

All paths are under `experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `src/step4_cluster_records/__init__.py`, `cluster.py`, and `run.py`
- Edit `SETUP.md` to add the step 4 command, and edit `RESULTS.md` under `## Step 4: clusters`

## Files forbidden to change

- `shared/**`
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
format_cluster_key(cluster_id: int) -> str
  Return f"cluster_{cluster_id:0{CLUSTER_ID_WIDTH}d}".

cluster_features(matrix: np.ndarray, min_cluster_size: int) -> tuple[np.ndarray, dict]
  resolve_hdbscan_params then fit_hdbscan. Return the labels and the params dict.
  Raise ValueError when matrix has fewer than 2 rows.

assign_clusters(features: pd.DataFrame, matrix: np.ndarray,
                feature_ids: list[str]) -> tuple[pd.DataFrame, dict]
  Return assignments with columns feature_id, cluster_id, and cluster_key, where
  cluster_key is None for noise, and one params dict for the single run.
  Raise ValueError when feature_ids does not match features.feature_id as a set.

summarize_clusters(assignments: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame
  Non-noise clusters only. Columns cluster_key, n_features, n_occurrences,
  n_batches, n_kept_side, n_removed_side, sorted by cluster_key.
```

`src/step4_cluster_records/run.py` has `main()`. It downloads the three step 3 files, clusters, and writes and uploads `ASSIGNMENTS_KEY`, `CLUSTER_SIZES_KEY`, and `CLUSTER_METADATA_KEY`. The metadata holds `SEED`, `HDBSCAN_MIN_CLUSTER_SIZE`, the params, the number of clusters, and the noise count. It prints one line.

## Commands

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
```

The run prints one line, where `D` is the feature count, `K` is the number of clusters, and `Z` is the number of noise features:

```text
features=D clusters=K noise=Z
```

Write those three numbers under `## Step 4: clusters` in `RESULTS.md`.

## Pass

`K` is at least 1, the number of clustered features plus `Z` equals the step 3 distinct count, and the three files are on S3.

## Fail

The step fails when the assignments miss a feature id, when the run splits the matrix by category, or when `StandardScaler` or KMeans is applied.
