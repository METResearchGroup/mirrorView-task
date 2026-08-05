# Step 7: Production run (500 keep + 500 remove) and RESULTS.md

## Goal

Only after **explicit user approval** of Step-6 smoke artifacts: run the pinned production sample — **500 keep** and **500 remove** posts — through all four stages, then write `experiments/create_llm_features_2026_08_05/RESULTS.md`.

## Approval gate (mandatory)

**Do not start this step until Step 6 smoke succeeded and the user explicitly approved.**

Before any `--sample-size 500` invocation:

1. Confirm Step 6 smoke completed for both classes (all four stages + four cluster PNGs).
2. Confirm the user has **explicitly approved** proceeding to production.
3. If approval is missing: **stop**. Do not sample 500. Do not write `RESULTS.md`.

## Pinned production budget (do not soften)

| Quantity | Value |
|----------|-------|
| Keep posts sampled | **500** (`--sample-size 500`) |
| Remove posts sampled | **500** (`--sample-size 500`) |
| Posts per feature-gen prompt | **10** (`--posts-per-batch 10`) |
| Keep feature-gen prompts | **50** (500 ÷ 10) |
| Remove feature-gen prompts | **50** (500 ÷ 10) |
| Max features per prompt | **8** |
| Features to embed (upper bound) | **800** (50×8 + 50×8) |
| Seed | **42** |
| Clustering | HDBSCAN + KMeans (both); **label HDBSCAN only** |
| Stage-4 `--sample-per-cluster` | **8** |

Sampling: without replacement within each class, seed `42`. Do **not** use `--sample-fraction 0.10` or any other size.

## Caller / unit of work

**In scope:** production end-to-end for keep and remove; `RESULTS.md`; README production command block with these exact numbers.

**Out of scope:** re-running smoke; labeling KMeans clusters; committing; editing `shared/**`; changing `pyproject.toml`; work under `experiments/create_llm_feature_clusters_2026_08_02/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| All four stage scripts under `experiments/create_llm_features_2026_08_05/src/` | CLI flags |
| Step-6 smoke artifact dirs + PNGs | Confirm approval basis |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` | RESULTS.md tone/structure reference |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` | Production commands |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/RESULTS.md` (create/overwrite with production summary)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (production block with 500/500 / 50+50 / ≤800)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/**` (production runs)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`
- Do not `git commit` unless the parent later asks

## Production procedure (after approval only)

```bash
cd /Users/mark/src/work/mirrorView-task

# --- KEEP production: 500 posts → 50 prompts → ≤400 features ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep --sample-size 500 --posts-per-batch 10 --seed 42
# Expect: 50 runner items; leftover_message_ids empty (500 % 10 == 0)
# Record KEEP_FEAT_DIR=.../outputs/generated_features/keep/outputs/<TS>

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep --features-run-dir "$KEEP_FEAT_DIR"
# Record KEEP_EMB_DIR=... ; n_features ≤ 400

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep --embeddings-run-dir "$KEEP_EMB_DIR" --seed 42
# Record KEEP_CLUS_DIR=...
# Expect: assignments_hdbscan.* + assignments_kmeans.* +
#   outputs/clusters/keep/cluster_hdbscan.png + cluster_kmeans.png

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep --clusters-run-dir "$KEEP_CLUS_DIR" --sample-per-cluster 8 --seed 42
# HDBSCAN clusters only
# Record KEEP_LAB_DIR=...

# --- REMOVE production: 500 posts → 50 prompts → ≤400 features ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class remove --sample-size 500 --posts-per-batch 10 --seed 42
# Expect: 50 runner items

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class remove --features-run-dir "$REMOVE_FEAT_DIR"

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class remove --embeddings-run-dir "$REMOVE_EMB_DIR" --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class remove --clusters-run-dir "$REMOVE_CLUS_DIR" --sample-per-cluster 8 --seed 42
```

### Expected LLM / feature counts

| Class | Posts | Feature-gen prompts | Features embedded (upper bound) |
|-------|-------|---------------------|---------------------------------|
| keep | 500 | 50 | ≤400 |
| remove | 500 | 50 | ≤400 |
| **Total** | **1000** | **100** | **≤800** |

Cluster-label LLM calls = number of non-noise HDBSCAN clusters per class (variable; record in RESULTS).

## RESULTS.md required contents

Create `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/RESULTS.md` with:

1. Date / seed `42` / sample rule: **exactly 500 keep + 500 remove** (not a fraction).
2. Budget line: 10 posts/batch → **50 keep + 50 remove** feature-gen prompts; ≤8 features/prompt → **≤800** features embedded.
3. Explicit note that Step-6 smoke was approved before this production run.
4. LLM model id: `gpt-5.4-nano`.
5. Embedding config: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized (`shared/embeddings/bedrock.py`).
6. Clustering: both HDBSCAN and KMeans run; **labels / RESULTS cluster table use HDBSCAN**; KMeans for comparison only.
7. Paths to the four class-root PNGs:
   - `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_hdbscan.png`
   - `experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_kmeans.png`
   - `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_hdbscan.png`
   - `experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_kmeans.png`
8. Per class (`keep`, `remove`):
   - n posts sampled (**500**), n feature batches (**50**), n features embedded (≤400; record actual)
   - HDBSCAN: n clusters, n noise, noise policy
   - KMeans: selected \(k\) (comparison note only)
   - path to Stage-4 labeled run directory
   - table of HDBSCAN `cluster_id → cluster_label` (and definition)
9. Absolute or repo-relative paths to all four production artifact roots used.

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Stage-1 production metadata should show sample_size=500, posts_per_batch=10
# (inspect the latest keep/remove feature-run metadata.json)

test -f experiments/create_llm_features_2026_08_05/RESULTS.md && echo 'RESULTS present'
grep -E '500|50 |800|HDBSCAN|hdbscan' experiments/create_llm_features_2026_08_05/RESULTS.md | head

test -s experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_hdbscan.png
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_kmeans.png
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_hdbscan.png
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_kmeans.png
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Approval | production only after explicit Step-6 approval | Ran 500/500 without approval |
| Sample sizes | exactly 500 keep + 500 remove; 50+50 prompts | Other sizes / `--sample-fraction 0.10` |
| Feature bound | n features embedded ≤800 total | Softened caps / unbounded run |
| Dual cluster | both methods’ assignments + four PNGs | HDBSCAN-only or KMeans-only |
| Labels | from HDBSCAN assignments | From KMeans |
| RESULTS.md | records 500/500, 50+50, ≤800, HDBSCAN source, PNG paths, labels | Missing numbers / smoke presented as production |
| Shared isolation | no diffs under `shared/` or `pyproject.toml` | Shared edits |

## Done when

- User approved Step-6 smoke.
- Production completed: **500 keep + 500 remove** → **50 + 50** feature prompts → ≤**800** features embedded → dual cluster → HDBSCAN labels.
- `RESULTS.md` summarizes production numbers, HDBSCAN labels, PNG paths, and artifact dirs.
- README documents the production command block with these exact pins.
