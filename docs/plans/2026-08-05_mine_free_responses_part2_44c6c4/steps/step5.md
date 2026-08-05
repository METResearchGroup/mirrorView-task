# Step 5: Label HDBSCAN clusters with Part-2-owned prompts

## Goal

Implement Part 2 Stage 4: for each non-noise HDBSCAN cluster, sample member features and ask `gpt-5.4-nano` (via `research_tools` runner) for a short label. Use **Part-2-owned** cluster-label prompts (free-response / Likert-group framing). Prefer `shared.feature_discovery.llm_based.schemas.ClusterLabelResult` for the response shape; do **not** label KMeans clusters.

**Edit the draft prompts in this file before implementing.**

## Caller / unit of work

```bash
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py \
  --likert-group low \
  --clusters-run-dir experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/low/<STAGE3_TS> \
  --sample-per-cluster 8 \
  --seed 42
```

(`--clusters-run-dir` optional → latest under `stage3_root(group)`)

**In scope:** Stage-4 module + Part-2-local cluster-label prompt builders (may live in `src/prompts.py` alongside Stage-1 prompts).

**Out of scope:** re-clustering; labeling KMeans; production full run; parent README; keep/remove edits.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py` | Load HDBSCAN assignments, sample members, runner wiring |
| `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/schemas.py` | Shared `ClusterLabelResult` |
| `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/paths.py` | `stage3_root` / `stage4_root` |
| Stage-3 `assignments_hdbscan.json` | Member `feature_id` + feature fields |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/prompts.py` (add cluster-label builders)
- Runtime artifacts under `part_2_mine_free_responses/outputs/generated_labels/{low,high}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/embed_features.py`
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/llm_based/cluster.py`
- Do **not** label from `assignments_kmeans.json`

## Contracts

### Input

1. Load `assignments_hdbscan.json` from the Stage-3 run dir (and feature text fields needed for sampling — same pattern as keep/remove Stage 4).
2. Group by `cluster_id`; **skip** `cluster_id == -1`.
3. For each remaining cluster, sample up to `--sample-per-cluster` (default **8**) member features with `seed`.
4. One runner item per cluster:

```python
{
  "cluster_id": int,
  "likert_group": "low" | "high",
  "n_members": int,
  "sampled_features": list[dict],  # feature_id, feature_name, feature_value, category, rationale, evidence_span, participant_id if present
}
```

### Output

- Model: `gpt-5.4-nano`
- Schema: `ClusterLabelResult` (`cluster_label`, `definition`, `salience_notes`)
- Runner `output_base_path=stage4_root(group)` → `outputs/generated_labels/{low|high}/outputs/{timestamp}/`
- Writer map includes `cluster_id`, `likert_group`, `n_members`, `sampled_feature_ids`, `result`

### Draft cluster-label prompts

**Low system (edit before implement):**

```text
You are labeling clusters of LLM-extracted themes from participant free responses
about how seeing original+mirror post pairs influenced keep/remove decisions.

This cluster comes from the LOW influence group (Likert < 4).

Given cluster_id and a random sample of member features, propose:
1. cluster_label (≤8 words) naming the shared theme
2. one-sentence definition usable in analysis of low-influence reflections
3. optional salience_notes (or empty string)

Base the label only on provided features. Do not invent themes.
Return structured JSON matching ClusterLabelResult.
```

**High:** same with high-influence / Likert `>= 4` wording.

## Exact commands

### Offline import check

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import generate_labels_for_embeddings as m
from shared.feature_discovery.llm_based.schemas import ClusterLabelResult
assert hasattr(m, 'main')
print('step5 label wiring OK')
"
```

### Live (requires OpenAI + Stage-3 HDBSCAN with ≥1 non-noise cluster)

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py \
  --likert-group low --sample-per-cluster 8 --seed 42
```

Expected: one JSON row per non-noise HDBSCAN cluster under `outputs/generated_labels/low/outputs/<ts>/`.

### Fail criteria

- Labels KMeans clusters
- Reuses keep/remove “KEEP/REMOVE posts” labeling prompts verbatim without free-response framing
- Parent README edited
- Skips QA-aware Stage-1 provenance (should still work if features exist)

## Done when

1. Stage-4 CLI labels HDBSCAN clusters for a group.
2. Artifacts under `outputs/generated_labels/{low,high}/outputs/{ts}/`.
3. Prompts are Part-2-owned free-response framing.
