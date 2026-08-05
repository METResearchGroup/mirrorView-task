# Step 1: Extract `shared/feature_discovery/llm_based/` from the keep/remove pipeline

## Goal

Create `shared/feature_discovery/llm_based/` by lifting domain-agnostic Stage-2 embedding and Stage-3 dual clustering/PNG logic (plus timestamp helpers and a generic cluster-label response shape) from `experiments/create_llm_features_2026_08_05/src/`. Part 2 will be the first consumer. **Do not** rewire keep/remove CLIs onto shared in this plan (leave that experiment’s Stage-2/3 modules as working copies).

## Caller / unit of work

**Main caller (offline import check):**

```bash
PYTHONPATH=. uv run python -c "
from shared.feature_discovery.llm_based import embed_features, cluster, paths, schemas
print('shared feature_discovery.llm_based OK')
"
```

**In scope:** new shared package only; copy/adapt logic from keep/remove Stage-2/3 helpers.

**Out of scope:** editing keep/remove experiment modules; Part 2 experiment code; live Bedrock/OpenAI calls; Stage-1 prompts; changing `shared/embeddings/bedrock.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/generate_embeddings.py` | Flatten Stage-1 features, Titan embed, write `features.jsonl` + `embeddings.npy` + `feature_ids.json` |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py` | Dual HDBSCAN + KMeans, silhouette \(k\), class-root PNGs |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/paths.py` | `latest_timestamp_subdir` helper to lift |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/schemas.py` | `ClusterLabelResult` only (generic); do **not** lift keep/remove `FeatureCategory` / `ExtractedFeature` |
| `/Users/mark/src/work/mirrorview-wt/shared/embeddings/bedrock.py` | `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS` — call as-is |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/__init__.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/__init__.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/paths.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/embed_features.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/cluster.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/schemas.py` (create)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**` (read only; do not thin-wrap)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/**`
- `/Users/mark/src/work/mirrorview-wt/shared/embeddings/bedrock.py`
- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- Do **not** create experiment `tests/` packages in this step

## Contracts to freeze

### Package layout

```text
shared/feature_discovery/
  __init__.py
  llm_based/
    __init__.py          # re-export public helpers used by Part 2
    paths.py             # make_run_timestamp, latest_timestamp_subdir
    embed_features.py    # load Stage-1 JSON → flatten → Titan → write artifacts
    cluster.py           # load Stage-2 → HDBSCAN+KMeans → assignments + PNGs
    schemas.py           # ClusterLabelResult only
```

### `paths.py`

- `make_run_timestamp() -> str` — local ISO-like stamp matching keep/remove Stage-2/3 style (`%Y-%m-%dT%H-%M-%S`).
- `latest_timestamp_subdir(parent: Path) -> Path` — newest child directory by name sort; raise `FileNotFoundError` if missing/empty.

### `embed_features.py` (path-parameterized; no experiment imports)

Public functions (names may match intent below; pick once and export from `__init__.py`):

1. `load_stage1_feature_rows(features_run_dir: Path) -> list[dict]` — all `*.json` except `metadata.json`.
2. `build_feature_embed_text(feature: dict) -> str` — exactly `{feature_name}: {feature_value}. {rationale}` stripped; raise `ValueError` if empty.
3. `extract_features_for_embedding(stage1_rows) -> list[dict]` — for each row, iterate `result["features"]`; skip empty; `feature_id = f"{batch_id}_{index_in_batch}"`; preserve provenance fields present on each feature including **`participant_id` and/or `message_id`**, plus `feature_name`, `feature_value`, `category`, `rationale`, `evidence_span`, `is_open_ended`, `text_embedded`.
4. `embed_feature_records(records) -> list[dict]` — call `shared.embeddings.bedrock.create_embedding` with defaults only (Titan v2, 256-d, L2-normalize); tqdm progress; assert model/dims/normalize.
5. `write_embedding_artifacts(*, output_root: Path, label_class: str, source_features_run_dir: Path, embedded_records: list[dict], run_timestamp: str) -> Path` — write under `output_root / run_timestamp/`:
   - `embeddings.npy` shape `(n, 256)` float64
   - `feature_ids.json`
   - `features.jsonl` (one record per line, including embedding vector)
   - `metadata.json` with `label_class`, `source_features_run_dir`, `model_id`, `dimensions`, `normalize`, `n_features`, `feature_id_scheme="batch_id_index_in_batch"`, `primary_format`

Raise `ValueError` if zero features after flatten (empty Stage-1 or all QA-rejected batches).

### `cluster.py` (path-parameterized)

Mirror keep/remove Stage-3 behavior:

1. Load `embeddings.npy` + `features.jsonl` (row-aligned) from a Stage-2 run dir.
2. `StandardScaler` fit on all rows; cluster on scaled matrix.
3. **HDBSCAN** (`sklearn.cluster.HDBSCAN`): `min_cluster_size=5`, `metric="euclidean"`; noise `cluster_id=-1` kept in assignments; metadata `hdbscan_noise_policy="skip_noise_for_labeling"`, `downstream_method="hdbscan"`.
4. **KMeans**: silhouette \(k\) selection same as keep/remove (`k` from 2 through `min(15, n-1)`; force `k=1` if `n < 4`); comparison only.
5. Write under `cluster_output_root / run_timestamp/`: `assignments_hdbscan.json`, `assignments_kmeans.json`, `metadata.json`, run-local PNG copies.
6. Also write/overwrite class-root PNGs at `class_png_dir / cluster_hdbscan.png` and `class_png_dir / cluster_kmeans.png` (caller passes `class_png_dir`, typically the class stage-3 root).

Do **not** add standalone `hdbscan` package; use sklearn only. Do **not** change `pyproject.toml`.

### `schemas.py`

Lift only:

```text
ClusterLabelResult: cluster_id, cluster_label (≤8 words), definition, salience_notes
```

Do **not** put keep/remove `FeatureCategory` or post `ExtractedFeature` in shared.

## Exact commands

### Pass

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from pathlib import Path
from shared.feature_discovery.llm_based.paths import make_run_timestamp, latest_timestamp_subdir
from shared.feature_discovery.llm_based.schemas import ClusterLabelResult
from shared.feature_discovery.llm_based import embed_features, cluster
assert callable(make_run_timestamp)
assert hasattr(embed_features, 'build_feature_embed_text')
assert hasattr(cluster, 'run_dual_clustering') or hasattr(cluster, 'cluster_embeddings')
print('step1 shared extract OK')
"
```

Expected stdout ends with: `step1 shared extract OK`

### Fail criteria

- Any edit under `experiments/create_llm_features_2026_08_05/`
- Shared imports experiment packages
- Shared embeds raw free-response text instead of feature name/value/rationale strings
- `pyproject.toml` changed or standalone `hdbscan` added

## Done when

1. `shared/feature_discovery/llm_based/` exists with the modules above.
2. Offline import check passes.
3. Keep/remove experiment files are byte-unchanged as call sites (this step does not thin-wrap them).
