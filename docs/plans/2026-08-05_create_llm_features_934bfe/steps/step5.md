# Step 5: Label HDBSCAN clusters with an LLM

## Goal

Implement `experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py` so each **HDBSCAN** cluster is one `research_tools.llm.runner.run` item: sample member feature texts, ask `gpt-5.4-nano` for a short cluster name/label (+ optional one-line definition), write under `outputs/generated_labels/{keep,remove}/`.

**Source of truth:** load Stage-3 `assignments_hdbscan.*` only. Do **not** label KMeans clusters (KMeans is comparison-only; see Step 4).

**Edit the draft prompts in this file before implementing.**

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep \
  --clusters-run-dir experiments/create_llm_features_2026_08_05/outputs/clusters/keep/<STAGE3_TS> \
  --sample-per-cluster 8 \
  --seed 42
```

**In scope:** Stage-4 labeling module + experiment-local label schema/prompt helpers under `src/`; runner wiring with tqdm via wrapped `writer_map_fn`; HDBSCAN-only cluster inputs.

**Out of scope:** changing clustering, re-embedding, labeling KMeans assignments, writing `RESULTS.md` (Step 7), theme synthesis over the full corpus (July-31 stage2), any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Runner + tqdm wrap pattern (reuse for labeling items) |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/stage2.py` | Second LLM stage runner pattern |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/prompts.py` | `THEME_SYNTHESIS_*` lineage (adapt to **per-cluster** labeling, not multi-theme corpus synthesis) |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/PLAN.md` | Labeling intent: short category label + optional one-line definition |
| Stage-3 `assignments_hdbscan.*` + `metadata.json` | HDBSCAN member features per `cluster_id` (ignore `assignments_kmeans.*`) |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/paths.py` (or `data.py`) | `stage4_root` |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py`
- Optional sibling under `src/` only: extend `src/schemas.py` / `src/prompts.py` with cluster-label schema + prompts
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (Stage-4 CLI)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/generated_labels/{keep,remove}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`
- Do not write `RESULTS.md` in this step

## Contracts

### Item construction

1. Load Stage-3 **`assignments_hdbscan.*`** from `--clusters-run-dir` (fail loudly if missing; do not fall back to KMeans).
2. Confirm `metadata.json` has `downstream_method="hdbscan"` when present.
3. Apply the Step-4 noise policy: **preferred** — skip `cluster_id == -1` (noise) for labeling; record `n_noise_skipped` in run metadata.
4. Group remaining rows by `cluster_id`.
5. For each cluster, sample up to `--sample-per-cluster` member features **without replacement** (`seed` + `cluster_id` as RNG salt so clusters are independent but reproducible). If cluster size ≤ sample size, use all members.
6. Each runner item:

```python
{
  "cluster_id": int,
  "label_class": "keep" | "remove",
  "n_members": int,
  "sampled_features": [
    {
      "feature_id": str,
      "message_id": str,
      "feature_name": str,
      "feature_value": str,
      "category": str,
      "rationale": str,
      "evidence_span": str | None,
    },
    ...
  ],
}
```

7. One runner item per non-noise HDBSCAN cluster (including singleton clusters). No KMeans items.

### Response schema (experiment-local)

```python
class ClusterLabelResult(BaseModel):
    cluster_id: int
    cluster_label: str = Field(description="Short human-readable category name (≤8 words).")
    definition: str = Field(description="One sentence defining the cluster for moderation analysis.")
    salience_notes: str = Field(
        description="Optional brief note on why these features cohere; empty string if none."
    )
```

### Runner wiring

1. `model="gpt-5.4-nano"`.
2. `output_base_path = stage4_root(label_class)` → writes  
   `experiments/create_llm_features_2026_08_05/outputs/generated_labels/{keep|remove}/outputs/{timestamp}/`.
3. `writer_map_fn` includes: `cluster_id`, `label_class`, `n_members`, sampled `feature_ids`, and `result.model_dump()`.
4. `run_metadata`: `stage="cluster_labeling"`, `label_class`, `source_clusters_run_dir`, `clustering_method="hdbscan"`, `sample_per_cluster`, `seed`, `model`, list of `cluster_ids`, `n_noise_skipped`.
5. tqdm via wrapped `writer_map_fn` (same constraint as Stage 1).

---

## Draft prompts (edit before implement)

> **Human edit gate:** revise the blocks below, then copy into `src/prompts.py` or `src/generate_labels_for_embeddings.py`.

### Cluster labeling — keep (system)

```
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated KEEP in a linked-fate keep/remove moderation task.

You will receive:
- cluster_id
- label_class: keep
- a random sample of member features from this cluster (feature_name, feature_value,
  category, rationale, optional evidence_span)

Task:
1. Propose a short cluster_label (≤8 words) that names the shared linguistic/rhetorical
   pattern in the sample.
2. Write a one-sentence definition usable as a moderation criterion for KEEP-rated posts.
3. Optionally add salience_notes (or empty string).

Rules:
- Base the label only on the provided features. Do not invent features not present.
- Prefer form/rhetoric/pragmatics over raw topic names when both are present
  (e.g. prefer "hedged policy prescription" over "guns").
- Do NOT predict keep/remove for new posts. Do NOT mention classifier error buckets.
- Return structured JSON matching ClusterLabelResult.
```

### Cluster labeling — keep (user template)

```
Label this KEEP-feature cluster.

cluster_id: {cluster_id}
n_members: {n_members}
sampled_features:
{sampled_features_json}
```

### Cluster labeling — remove (system)

```
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated REMOVE in a linked-fate keep/remove moderation task.

You will receive:
- cluster_id
- label_class: remove
- a random sample of member features from this cluster (feature_name, feature_value,
  category, rationale, optional evidence_span)

Task:
1. Propose a short cluster_label (≤8 words) that names the shared linguistic/rhetorical
   pattern in the sample.
2. Write a one-sentence definition usable as a moderation criterion for REMOVE-rated posts.
3. Optionally add salience_notes (or empty string).

Rules:
- Base the label only on the provided features. Do not invent features not present.
- Prefer form/rhetoric/pragmatics over raw topic names when both are present
  (e.g. prefer "emphatic outgroup ridicule" over "immigration").
- Do NOT predict keep/remove for new posts. Do NOT mention classifier error buckets.
- Return structured JSON matching ClusterLabelResult.
```

### Cluster labeling — remove (user template)

```
Label this REMOVE-feature cluster.

cluster_id: {cluster_id}
n_members: {n_members}
sampled_features:
{sampled_features_json}
```

### Message builder contract

```python
def build_cluster_label_messages(item: dict) -> list[dict[str, str]]:
    # sampled_features_json = json.dumps(item["sampled_features"], indent=2)
    # choose keep vs remove system/user templates from item["label_class"]
    # return [{"role":"system","content":...}, {"role":"user","content":...}]
```

---

## Exact commands

### Offline wiring

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from experiments.create_llm_features_2026_08_05.src import generate_labels_for_embeddings as m
from research_tools.llm.runner import run as _run
assert hasattr(m, 'main') or hasattr(m, 'run_cluster_labeling')
print('label wiring OK')
"
```

### Live label (requires `OPENAI_API_KEY` + Stage-3 artifacts)

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep \
  --clusters-run-dir experiments/create_llm_features_2026_08_05/outputs/clusters/keep/STAGE3_TS \
  --sample-per-cluster 8 \
  --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class remove \
  --clusters-run-dir experiments/create_llm_features_2026_08_05/outputs/clusters/remove/STAGE3_TS \
  --sample-per-cluster 8 \
  --seed 42
```

Expect timestamp folders under:

- `experiments/create_llm_features_2026_08_05/outputs/generated_labels/keep/outputs/`
- `experiments/create_llm_features_2026_08_05/outputs/generated_labels/remove/outputs/`

with one JSON row per cluster containing `result.cluster_label`.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Source | reads `assignments_hdbscan.*` only | Reads / falls back to KMeans |
| Coverage | one label row per non-noise HDBSCAN `cluster_id` | Missing/extra clusters; labels noise without documenting policy |
| Model | `gpt-5.4-nano` | Other id |
| Prompt class | keep vs remove system prompts differ | Single mixed prompt ignoring label_class |
| Paths | under `outputs/generated_labels/{keep,remove}/outputs/{ts}/` | Writing into clusters tree |
| Not theme synthesis | schema is per-cluster label, not July-31 `ThemeSynthesisResult` multi-theme corpus dump | Reused stage2 theme synthesis unchanged |

## Done when

- Keep and remove **HDBSCAN** clusters are labeled via the research_tools runner.
- KMeans assignments are never labeled.
- Prompts in code match the human-edited drafts above.
- Artifacts land under `outputs/generated_labels/{keep,remove}/`.
- Offline wiring passes; live labeling succeeds when credentials and HDBSCAN cluster artifacts exist.
