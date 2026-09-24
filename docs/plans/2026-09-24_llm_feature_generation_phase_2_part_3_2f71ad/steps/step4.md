# Step 4: Normalize features (embed, cluster, name)

Embed all discovered feature texts with Amazon Titan, cluster embeddings with HDBSCAN (primary) and K-Means (comparison), name HDBSCAN clusters with `gpt-6-luna` via `llm_client.py`, and report cluster stability across three random seeds and across text arms. All outputs live under `outputs/<arm>/normalize/`.

## Scope

- **Callers / entrypoints:** `generate_embeddings`, `cluster_embeddings`, and `label_clusters` CLIs (`if __name__ == "__main__"` each).
- **In scope:**
  - `generate_embeddings.py`: flatten Step 3 mixed-discovery JSON into `features.jsonl`, embed `text_embedded` with `shared.embeddings.bedrock.create_embedding` (256-d, L2 normalized).
  - `cluster_embeddings.py`: HDBSCAN (primary) + K-Means k-sweep (k=2..10) per arm; run seeds 42, 43, 44; write stability metrics (adjusted Rand index within arm across seed pairs).
  - `label_clusters.py`: for each HDBSCAN cluster (skip noise id `-1`), sample member features, call `llm_client.complete_structured` with `ClusterLabelResult` from Step 3 `schemas.py` and `build_cluster_label_messages` from Step 3 `prompts.py`.
  - Cross-arm stability summary comparing per-arm seed stability and cluster counts.
  - Unit tests: mock Bedrock embeddings and mock `llm_client` (no network in pytest).
- **Out of scope:**
  - Shared codebook merge (Step 5).
  - Post labeling (Step 6).
  - Editing Step 3 modules except reading `llm_client.py`.
  - Single-class ablation discovery runs (optional secondary input; primary path uses mixed discovery).

## Files to inspect (read-only)

- `experiments/create_llm_features_2026_08_05/src/generate_embeddings.py` - feature flattening, `build_feature_embed_text`, Titan calls, `embeddings.npy` layout.
- `experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py` - HDBSCAN params, K-Means sweep, assignment JSON files, PCA PNG optional.
- `experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py`: cluster sampling and runner row shape (copy ideas only).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/prompts.py`: `build_cluster_label_messages` (Step 3 owner; import only).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/schemas.py`: `ClusterLabelResult` (Step 3 owner; import only).
- `shared/embeddings/bedrock.py` - `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/llm_client.py` - `complete_structured`, cost log (from Step 3).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/paths.py` - `normalize_run_dir`, `discovery_run_dir`, `latest_timestamp_subdir` (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/constants.py` - `CLUSTER_SEEDS`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_NORMALIZE` (from Step 1).
- `experiments/model_errors_analysis_2026_07_15/analyze/cluster.py` - `adjusted_rand_score` usage pattern (read-only reference).

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/generate_embeddings.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/cluster_embeddings.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/label_clusters.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_embeddings.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cluster_embeddings.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_clusters.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/<arm>/normalize/**` - embeddings, clusters, labels, stability reports (gitignored).

## Files forbidden to change

- `shared/` (read-only; call `create_embedding` only).
- Other `experiments/*` (no cross-experiment imports).
- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md` and sibling step files.
- Step 3 modules (read-only): `batching.py`, `prompts.py`, `schemas.py`, `generate_features.py`, `llm_client.py`. **Do not edit `prompts.py` or `schemas.py`.** At import time, fail fast with a clear error if `ClusterLabelResult` or `build_cluster_label_messages` is missing from Step 3 modules.
- Step 1/2 modules (read-only).
- `lib/` (read-only).

## Contract overrides (orchestrator wins)

1. **Timestamp format:** `%Y-%m-%dT%H-%M-%S` local time for all normalize output folders (embed, cluster per seed, labels).
2. **Cluster label outputs:** store under `outputs/<arm>/normalize/<embed_timestamp>/clusters_seed_<seed>/labels/<label_timestamp>/` (not `outputs/<arm>/operationalize/` from contract Section 6.6).
3. **LLM cluster naming:** use Step 3 `llm_client.complete_structured` with `model="openai/gpt-6-luna"` and `reasoning_effort="none"` (not `research_tools` runner).

## Implementation phases (TDD - mandatory order)

| Phase | Goal | Gate |
|-------|------|------|
| 1 - Scope | Name callers, output tree, out-of-scope | Three CLIs + tree listed |
| 2 - Scaffold | Create modules; stub bodies only | Imports resolve; `raise NotImplementedError` |
| 3 - Contracts | Types, signatures, artifact paths | Matches Sections 6.4-6.5; stubs only |
| 4 - Test design | Failing tests (happy + key failures) | Tests fail for the right reason |
| 5 - Implement | One function/path per commit until green | Targeted tests pass |
| 6 - Done | Step pytest + CLI on smoke discovery outputs | Pass/fail criteria met |

### Phase 1 - Output tree

```text
outputs/<arm>/normalize/
  <embed_timestamp>/
    features.jsonl
    embeddings.npy
    feature_ids.json
    metadata.json
    clusters_seed_42/
      assignments_hdbscan.json
      assignments_kmeans.json
      cluster_sizes_hdbscan.json
      k_selection.json
      metadata.json
      labels/
        <label_timestamp>/
          NNNNN_<call_timestamp>.json   # per cluster via llm_client
          metadata.json
    clusters_seed_43/
      ...
    clusters_seed_44/
      ...
    stability_within_arm.json
  stability_across_arms.json            # written once after all arms complete
```

Primary input: latest **mixed** discovery run at `outputs/<arm>/discovery/outputs/<discovery_timestamp>/` unless `--discovery-run-dir` is set.

### Phase 3 - Contract signatures

**`generate_embeddings.py`**

```python
def make_run_timestamp() -> str: ...  # "%Y-%m-%dT%H-%M-%S"

def resolve_discovery_run_dir(arm: str, discovery_run_dir: str | None) -> Path: ...

def load_discovery_feature_rows(discovery_run_dir: Path) -> list[dict[str, Any]]: ...
# Reads per-call JSON; extracts batch fields from top-level key `discovery_row` (required).

def build_feature_embed_text(feature: dict[str, Any]) -> str: ...
# Returns "{feature_name}: {feature_value}. {rationale}"; raises ValueError if empty.

def flatten_discovery_to_features(
    discovery_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]: ...
# Each record: feature_id, batch_id, message_id, feature_name, feature_value,
# category, rationale, evidence_span, text_embedded

def embed_features(
    records: list[dict[str, Any]],
) -> np.ndarray: ...  # shape (n, 256), float32

def write_embedding_artifacts(
    output_dir: Path,
    records: list[dict[str, Any]],
    matrix: np.ndarray,
    metadata: dict[str, Any],
) -> Path: ...
```

CLI: `--arm` (required), `--discovery-run-dir` (optional), `--batch-design mixed` (default; error if metadata says otherwise).

**`cluster_embeddings.py`**

```python
def resolve_embeddings_run_dir(arm: str, embeddings_run_dir: str | None) -> Path: ...

def load_embeddings(embeddings_run_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]]]: ...

def run_hdbscan(
    matrix: np.ndarray,
    *,
    min_cluster_size: int = 5,
    seed: int,
) -> np.ndarray: ...  # label per row; -1 = noise

def run_kmeans_sweep(
    matrix: np.ndarray,
    *,
    k_min: int = 2,
    k_max: int = 10,
    seed: int,
) -> tuple[dict[str, Any], np.ndarray]: ...
# k_selection.json content + best-k assignment vector

def assignments_to_json(labels: np.ndarray, feature_ids: list[str]) -> dict[str, int]: ...

def compute_seed_pair_ari(
    assignments_a: dict[str, int],
    assignments_b: dict[str, int],
) -> float: ...  # sklearn.metrics.adjusted_rand_score on aligned feature_ids

def write_cluster_artifacts(
    output_dir: Path,
    *,
    hdbscan_labels: np.ndarray,
    kmeans_labels: np.ndarray,
    k_selection: dict[str, Any],
    feature_ids: list[str],
    metadata: dict[str, Any],
) -> Path: ...
```

CLI: `--arm`, `--embeddings-run-dir`, `--seed` (one of 42, 43, 44 per run).

After all three seeds for an arm: write `stability_within_arm.json` at embed timestamp root:

```json
{
  "arm": "original_only",
  "seeds": [42, 43, 44],
  "adjusted_rand_index": {
    "42_43": 0.0,
    "42_44": 0.0,
    "43_44": 0.0
  },
  "mean_ari": 0.0,
  "hdbscan_cluster_counts": {"42": 0, "43": 0, "44": 0},
  "noise_fraction": {"42": 0.0, "43": 0.0, "44": 0.0}
}
```

**`label_clusters.py`**

```python
def load_hdbscan_assignments(clusters_run_dir: Path) -> dict[str, int]: ...

def build_cluster_label_items(
    assignments: dict[str, int],
    feature_records: list[dict[str, Any]],
    *,
    sample_per_cluster: int = 8,
    seed: int,
) -> list[dict[str, Any]]: ...
# Skip cluster_id == -1. Each item: cluster_id, arm, seed, n_members,
# sampled_features (list of feature dicts with feature_id)

def label_clusters_for_run(
    items: list[dict[str, Any]],
    *,
    arm: str,
    seed: int,
    output_dir: Path,
) -> Path: ...
# Calls llm_client.complete_structured with ClusterLabelResult; stage="cluster_label"
```

CLI: `--arm`, `--clusters-run-dir` (path to `clusters_seed_<seed>/`), `--seed`, `--sample-per-cluster` (default 8).

Cluster label row (per cluster JSON, top-level key `cluster_label_row` only):

| Field | Type |
|-------|------|
| `cluster_id` | int |
| `arm` | str |
| `seed` | int |
| `n_members` | int |
| `sampled_feature_ids` | list[str] |
| `result` | `ClusterLabelResult` |

**Cross-arm report** (`stability_across_arms.json` at `outputs/shared/normalize/` or repo-root experiment `outputs/shared/normalize/`):

```json
{
  "arms": ["original_only", "mirror_only", "paired"],
  "per_arm_mean_ari": {"original_only": 0.0, "mirror_only": 0.0, "paired": 0.0},
  "per_arm_hdbscan_cluster_count_median": {"original_only": 0, "mirror_only": 0, "paired": 0},
  "per_arm_noise_fraction_median": {"original_only": 0.0, "mirror_only": 0.0, "paired": 0.0},
  "note": "Cross-arm ARI not defined (distinct feature_id sets per arm); compare stability summaries."
}
```

### Phase 4 - Test design (named tests and assertions)

**`test_generate_embeddings.py`** (mock `shared.embeddings.bedrock.create_embedding`)

| Test | Given | When | Then |
|------|-------|------|------|
| `test_flatten_mixed_discovery_row` | one mixed discovery JSON with 2 keep + 1 remove features | `flatten_discovery_to_features` | 3 records; each has `feature_id`, `text_embedded` |
| `test_build_feature_embed_text_format` | feature dict | `build_feature_embed_text` | equals `name: value. rationale` |
| `test_embed_features_shape` | 5 records, mock returns 256-d vector | `embed_features` | ndarray shape `(5, 256)` |
| `test_write_embedding_artifacts_files` | records + matrix | `write_embedding_artifacts` | dir contains `features.jsonl`, `embeddings.npy`, `feature_ids.json`, `metadata.json` |
| `test_feature_ids_align_with_matrix` | written artifacts | load | `len(feature_ids) == embeddings.npy.shape[0]` |

**`test_cluster_embeddings.py`**

| Test | Given | When | Then |
|------|-------|------|------|
| `test_hdbscan_returns_labels` | random `(20, 256)` matrix | `run_hdbscan` | int label array length 20 |
| `test_kmeans_sweep_writes_k_selection` | matrix | `run_kmeans_sweep` | `k_selection` has keys for k=2..10 with `silhouette` or `inertia` |
| `test_assignments_json_maps_feature_ids` | labels + ids | `assignments_to_json` | keys are feature_id strings |
| `test_seed_pair_ari_identical_assignments` | same assignments twice | `compute_seed_pair_ari` | ARI == 1.0 |
| `test_seed_pair_ari_random_assignments` | unrelated label vectors | `compute_seed_pair_ari` | ARI near 0.0 (loose bound -0.2 to 0.2) |
| `test_stability_within_arm_json_schema` | three seed dirs | aggregate helper | JSON has `adjusted_rand_index` with keys `42_43`, `42_44`, `43_44` |

**`test_label_clusters.py`** (mock `llm_client.complete_structured`)

| Test | Given | When | Then |
|------|-------|------|------|
| `test_skips_noise_cluster` | assignments with `-1` | `build_cluster_label_items` | no item with `cluster_id == -1` |
| `test_sample_per_cluster_cap` | cluster with 20 members | `sample_per_cluster=8` | item has at most 8 sampled features |
| `test_label_clusters_writes_one_file_per_cluster` | 3 non-noise clusters | `label_clusters_for_run` | 3 per-call JSON files (mocked LLM) |
| `test_cluster_label_row_shape` | one labeled cluster | inspect output | has `cluster_id`, `arm`, `seed`, `result.cluster_label` |

### Phase 5 - Implementation order

1. `generate_embeddings.py` (flatten + mockable embed).
2. `cluster_embeddings.py` (HDBSCAN + K-Means + ARI).
3. `label_clusters.py` (imports `build_cluster_label_messages` from Step 3 `prompts.py` and `ClusterLabelResult` from Step 3 `schemas.py`; uses `llm_client.complete_structured`).
4. Cross-arm stability aggregator (small function in `cluster_embeddings.py` or `label_clusters.py` `if __name__` helper).
5. Green all tests.

## Pass / fail criteria

### Must pass

- Embeddings: `embeddings.npy` shape `(n_features, 256)`; `metadata.json` has `bedrock_model_id=amazon.titan-embed-text-v2:0`, `dimensions=256`, `normalize=true`.
- HDBSCAN assignments written to `assignments_hdbscan.json`; K-Means to `assignments_kmeans.json`.
- Three seeds (42, 43, 44) per arm produce three `clusters_seed_<seed>/` directories.
- `stability_within_arm.json` exists per arm with pairwise ARI for all three seed pairs.
- `stability_across_arms.json` exists after all arms processed.
- Cluster labeling skips noise (`cluster_id == -1`).
- Every cluster label LLM call uses `reasoning_effort="none"` via `llm_client`.
- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_embeddings.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cluster_embeddings.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_clusters.py -q` - exit 0.

### Must fail (until implemented)

- `test_skips_noise_cluster` before noise filter exists.
- `test_seed_pair_ari_identical_assignments` before ARI helper exists.
- `test_feature_ids_align_with_matrix` before alignment checks exist.

## Commands (exact)

Export AWS before Bedrock calls:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

ARM=original_only
DISCOVERY_DIR=outputs/$ARM/discovery/outputs/<discovery_timestamp>

# 1. Embed features (once per arm)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_embeddings \
  --arm "$ARM" \
  --discovery-run-dir "$DISCOVERY_DIR"

EMB_DIR=outputs/$ARM/normalize/<embed_timestamp>

# 2. Cluster + label per seed
for SEED in 42 43 44; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cluster_embeddings \
    --arm "$ARM" \
    --embeddings-run-dir "$EMB_DIR" \
    --seed "$SEED"

  CLUSTER_DIR=outputs/$ARM/normalize/<embed_timestamp>/clusters_seed_$SEED

  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_clusters \
    --arm "$ARM" \
    --clusters-run-dir "$CLUSTER_DIR" \
    --seed "$SEED" \
    --sample-per-cluster 8
done

# Repeat for mirror_only and paired

# 3. Cross-arm stability summary (after all arms)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cluster_embeddings \
  --write-cross-arm-stability

# Tests (mocked Bedrock + mocked llm_client)
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_embeddings.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cluster_embeddings.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_clusters.py -q
```

Implement `--write-cross-arm-stability` as a `cluster_embeddings.py` subcommand or flag that reads each arm's `stability_within_arm.json` and writes `outputs/shared/normalize/stability_across_arms.json`.

### Expected output (representative lines)

**`generate_embeddings`:**

```
arm=original_only n_features=1842 embeddings.npy shape=(1842, 256)
Wrote outputs/original_only/normalize/2026-09-24T15-20-01/
```

**`cluster_embeddings`:**

```
arm=original_only seed=42 hdbscan_clusters=47 noise_fraction=0.08 kmeans_best_k=6
Wrote outputs/original_only/normalize/2026-09-24T15-20-01/clusters_seed_42/
stability_within_arm mean_ari=0.72
```

**`label_clusters`:**

```
arm=original_only seed=42 clusters_labeled=45 skipped_noise=127
Wrote outputs/original_only/normalize/2026-09-24T15-20-01/clusters_seed_42/labels/2026-09-24T15-25-10/
```

**pytest:**

```
..................
18 passed in 0.62s
```

## Artifact contract (this step's outputs)

### Embeddings (`outputs/<arm>/normalize/<embed_timestamp>/`)

| File | Schema |
|------|--------|
| `features.jsonl` | One JSON per line: `feature_id`, `batch_id`, `message_id`, `feature_name`, `feature_value`, `category`, `rationale`, `evidence_span`, `text_embedded` |
| `embeddings.npy` | `(n_features, 256)` float |
| `feature_ids.json` | list[str] aligned to rows |
| `metadata.json` | `arm`, `discovery_run_dir`, `bedrock_model_id`, `dimensions`, `normalize`, `timestamp_format` |

### Cluster outputs (`outputs/<arm>/normalize/<embed_timestamp>/clusters_seed_<seed>/`)

| File | Content |
|------|---------|
| `assignments_hdbscan.json` | `{ "feature_id": cluster_id, ... }` (`-1` = noise) |
| `assignments_kmeans.json` | same shape |
| `cluster_sizes_hdbscan.json` | `{ "cluster_id": count }` |
| `k_selection.json` | K-Means sweep metrics k=2..10 |
| `metadata.json` | `seed`, `arm`, `embeddings_run_dir`, `downstream_method` (`hdbscan`) |
| `stability_within_arm.json` | written at embed root after all seeds (see schema above) |

### Cluster labels (`.../clusters_seed_<seed>/labels/<label_timestamp>/`)

Per-cluster JSON via `llm_client` plus row fields listed in Phase 3. `metadata.json` includes `model`, `reasoning_effort`, `arm`, `seed`, `stage=cluster_label`.

### Shared stability (`outputs/shared/normalize/stability_across_arms.json`)

Schema in Phase 3 cross-arm section.

## Human gates

None for Step 4. Step 3 Gate A must be satisfied before Step 3 production discovery that feeds this step.

## Commit message template

`step4: {short description}`

Examples: `step4: flatten discovery features and Titan embeddings`, `step4: HDBSCAN clustering with seed stability ARI`, `step4: LLM cluster labels via llm_client`.

## Handoff to Step 5

**Deliverables:**

- Per arm: `outputs/<arm>/normalize/<embed_timestamp>/` with embeddings, three `clusters_seed_*` dirs, labeled clusters under each seed's `labels/` folder.
- `outputs/<arm>/normalize/<embed_timestamp>/stability_within_arm.json`.
- `outputs/shared/normalize/stability_across_arms.json`.

**Step 5 reads:**

- `outputs/<arm>/normalize/<embed_timestamp>/features.jsonl`
- `outputs/<arm>/normalize/<embed_timestamp>/clusters_seed_<seed>/assignments_hdbscan.json` (default seed `42`)
- Cluster labels at `outputs/<arm>/normalize/<embed_timestamp>/clusters_seed_<seed>/labels/<label_timestamp>/`
- Primary path: mixed-discovery + normalize outputs for all three arms.

**Convention for Step 5:** use seed `42` cluster labels as the default primary input; document in Step 5 if multi-seed merge is required.
