# Step 4: Wire Stages 2–3 through shared

## Goal

Implement Part 2 Stage-2 and Stage-3 CLIs as thin callers of `shared/feature_discovery/llm_based/` (from Step 1). Stage 2 embeds Stage-1 feature texts with Titan; Stage 3 runs dual HDBSCAN + KMeans and writes comparison PNGs. Do not re-implement embed/cluster logic in the experiment package.

## Caller / unit of work

**Stage 2:**

```bash
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \
  --likert-group low \
  --features-run-dir experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/generated_features/low/outputs/<STAGE1_TS>
```

(`--features-run-dir` optional → latest under `stage1_root(group)/outputs/`)

**Stage 3:**

```bash
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \
  --likert-group low \
  --embeddings-run-dir experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/generated_embeddings/low/<STAGE2_TS> \
  --seed 42
```

**In scope:** Part 2 `generate_embeddings.py` and `cluster_embeddings.py` only (CLI + path wiring).

**Out of scope:** Stage-1/4; editing shared algorithms beyond bugfixes required to call them; editing keep/remove; parent README; `RESULTS.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/embed_features.py` | Shared Stage-2 API from Step 1 |
| `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/cluster.py` | Shared Stage-3 API from Step 1 |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/generate_embeddings.py` | CLI flag shape reference |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py` | CLI + PNG path reference |
| `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/paths.py` | `stage2_root` / `stage3_root` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py`
- Runtime artifacts under `part_2_mine_free_responses/outputs/generated_embeddings/{low,high}/` and `outputs/clusters/{low,high}/`
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/**` only if a Step-1 API gap blocks wiring (prefer fix shared once; do not fork logic back into the experiment)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/embeddings/bedrock.py`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- Stage-1 / Stage-4 modules (except import-only if needed)

## Contracts

### Stage 2 CLI responsibilities

1. Validate `--likert-group` via `paths`.
2. Resolve Stage-1 run dir (explicit or latest).
3. Call shared: load → flatten → embed → `write_embedding_artifacts(output_root=stage2_root(group), label_class=group, ...)`.
4. Print output directory path.
5. If Stage-1 produced zero features after QA (entire run empty), fail with a clear `ValueError` from shared (document in stderr). Smoke must use batches that yield ≥1 feature or re-smoke Stage 1.

Provenance: feature records may carry `participant_id` (not `message_id`); shared flatten must already preserve it from Step 1.

### Stage 3 CLI responsibilities

1. Resolve Stage-2 run dir (explicit or latest under `stage2_root`).
2. Call shared dual clustering with:
   - `cluster_output_root=stage3_root(group)`
   - `class_png_dir=stage3_root(group)` (class-root PNGs)
   - `seed=42` default
3. Exact class-root PNG paths:

| Path |
|------|
| `.../part_2_mine_free_responses/outputs/clusters/low/cluster_hdbscan.png` |
| `.../part_2_mine_free_responses/outputs/clusters/low/cluster_kmeans.png` |
| `.../part_2_mine_free_responses/outputs/clusters/high/cluster_hdbscan.png` |
| `.../part_2_mine_free_responses/outputs/clusters/high/cluster_kmeans.png` |

4. Downstream labeling (Step 5) consumes **HDBSCAN** only; skip `cluster_id=-1`.

### Artifact formats (same as keep/remove)

| Stage | Primary artifacts |
|-------|-------------------|
| 2 | `{ts}/features.jsonl` + `embeddings.npy` + `feature_ids.json` + `metadata.json` |
| 3 | `{ts}/assignments_hdbscan.json`, `assignments_kmeans.json`, `metadata.json`, PNGs |

## Exact commands

### Offline import check

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import generate_embeddings as e
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import cluster_embeddings as c
assert hasattr(e, 'main') and hasattr(c, 'main')
print('step4 cli wiring OK')
"
```

### Live (requires AWS + prior Stage-1 artifacts with ≥1 feature)

```bash
cd /Users/mark/src/work/mirrorview-wt

# After Step-3 low smoke:
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \
  --likert-group low

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \
  --likert-group low --seed 42
```

Expected: Stage-2 and Stage-3 timestamp dirs created; class-root PNGs present for that group.

### Fail criteria

- Experiment reimplements Titan loop or HDBSCAN/KMeans instead of calling shared
- PNGs only under timestamp dir and missing at class root
- `pyproject.toml` / standalone `hdbscan` added
- Parent README edited

## Done when

1. Stage-2/3 CLIs call shared and write under Part 2 `outputs/`.
2. Offline import check passes; live path works on a Stage-1 smoke with ≥1 feature.
3. Four class-root PNG paths exist after both groups are clustered (low+high may be completed in Step 6).
