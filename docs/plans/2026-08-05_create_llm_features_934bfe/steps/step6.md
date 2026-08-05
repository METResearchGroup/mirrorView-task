# Step 6: Smoke both classes end-to-end (approval gate)

## Goal

Run a tiny live path for **both** keep and remove through all four stages, confirm artifacts land in the four `outputs/` subtrees (including dual-cluster PNGs and HDBSCAN-based labels), then **stop and wait for explicit user approval** before Step 7.

This step is **smoke-only**. It does **not** run the 500/500 production sample. It does **not** write production `RESULTS.md` (that is Step 7).

## Approval gate (mandatory)

**Do not start Step 7 until the user explicitly approves after reviewing smoke artifacts.**

Before any production invocation (Step 7):

1. Confirm smoke completed for both `keep` and `remove` (all four stages).
2. Confirm both HDBSCAN and KMeans PNGs exist for both classes.
3. Confirm Stage-4 labels came from **HDBSCAN** assignments (not KMeans).
4. Confirm the user has **explicitly approved** proceeding to production after reviewing those artifacts.
5. If approval is missing: **stop**. Do not run `--sample-size 500`. Do not write `RESULTS.md` as if production finished.

## Caller / unit of work

**Smoke caller (exact sizes):**

| Flag | Smoke value |
|------|-------------|
| `--sample-size` (Stage 1) | `10` posts per class |
| `--posts-per-batch` | `10` (⇒ 1 batch / 1 feature-gen prompt per class) |
| Max features per prompt | `8` |
| `--sample-per-cluster` (Stage 4) | `min(8, cluster_size)` |
| `--seed` | `42` |
| Clustering | both HDBSCAN + KMeans; label **HDBSCAN** only |

**Production sizes are Step 7 only:** `--sample-size 500` per class → 50+50 prompts → ≤800 features. Do not invoke them here.

**In scope:** end-to-end smoke for both classes; README notes for smoke vs production + approval gate pointing to Step 7.

**Out of scope:** production 500/500 run; writing production `RESULTS.md`; committing; editing `shared/**`; implementing under `experiments/create_llm_feature_clusters_2026_08_02/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| All four stage scripts under `experiments/create_llm_features_2026_08_05/src/` | CLI flags and artifact paths |
| Smoke Stage-1…4 output dirs for keep and remove | Verify before asking for approval |
| Class-root cluster PNGs | Visual comparison before approval |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` | Update smoke vs production commands |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-08-05_create_llm_features_934bfe/steps/step7.md` | Production sizes after approval |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (smoke vs production + approval gate → Step 7)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/**` (smoke only)
- Minor CLI fixes in the four `src/` stage scripts **only** if smoke reveals broken flags/paths (no scope expansion)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/RESULTS.md` — do **not** create/overwrite as production results in this step
- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`
- Do not `git commit` unless the parent later asks

## Smoke procedure (exact)

Run from repo root. Requires `OPENAI_API_KEY` in repo-root `.env` and AWS credentials for Bedrock.

```bash
cd /Users/mark/src/work/mirrorView-task

# --- KEEP smoke ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep --sample-size 10 --posts-per-batch 10 --seed 42
# Record KEEP_FEAT_DIR=.../outputs/generated_features/keep/outputs/<TS>
# Expect: 1 feature-gen prompt, ≤8 features

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep --features-run-dir "$KEEP_FEAT_DIR"
# Record KEEP_EMB_DIR=.../outputs/generated_embeddings/keep/<TS>

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep --embeddings-run-dir "$KEEP_EMB_DIR" --seed 42
# Record KEEP_CLUS_DIR=.../outputs/clusters/keep/<TS>
# Expect: assignments_hdbscan.* + assignments_kmeans.* + PNGs

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep --clusters-run-dir "$KEEP_CLUS_DIR" --sample-per-cluster 8 --seed 42
# Labels HDBSCAN clusters only
# Record KEEP_LAB_DIR=.../outputs/generated_labels/keep/outputs/<TS>

# --- REMOVE smoke ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class remove --sample-size 10 --posts-per-batch 10 --seed 42
# Record REMOVE_FEAT_DIR=...

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class remove --features-run-dir "$REMOVE_FEAT_DIR"

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class remove --embeddings-run-dir "$REMOVE_EMB_DIR" --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class remove --clusters-run-dir "$REMOVE_CLUS_DIR" --sample-per-cluster 8 --seed 42
```

### Smoke pass checklist

| Check | Pass |
|-------|------|
| Stage 1 keep | `metadata.json` + ≥1 item JSON under `outputs/generated_features/keep/outputs/<TS>/`; 1 batch |
| Stage 1 remove | same under `.../remove/...` |
| Stage 2 keep/remove | embeddings metadata `dimensions=256`, `model_id=amazon.titan-embed-text-v2:0` |
| Stage 3 keep/remove | both `assignments_hdbscan.*` and `assignments_kmeans.*`; `downstream_method=hdbscan` |
| Stage 3 PNGs | all four class-root PNGs exist (see verification commands) |
| Stage 4 keep/remove | one label per **HDBSCAN** non-noise cluster; `cluster_label` non-empty; metadata notes HDBSCAN source |
| Class split | no keep artifacts written under remove paths (and vice versa) |

**Stop here and ask the user to review smoke artifacts (including the four cluster PNGs) before Step 7.**

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

# After smoke: directories must exist (adjust timestamps)
ls experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/
ls experiments/create_llm_features_2026_08_05/outputs/generated_features/remove/outputs/
ls experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/keep/
ls experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/remove/
ls experiments/create_llm_features_2026_08_05/outputs/clusters/keep/
ls experiments/create_llm_features_2026_08_05/outputs/clusters/remove/
ls experiments/create_llm_features_2026_08_05/outputs/generated_labels/keep/outputs/
ls experiments/create_llm_features_2026_08_05/outputs/generated_labels/remove/outputs/

# Dual-method PNG comparison (exact paths)
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_hdbscan.png && echo 'keep hdbscan png OK'
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/keep/cluster_kmeans.png && echo 'keep kmeans png OK'
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_hdbscan.png && echo 'remove hdbscan png OK'
test -s experiments/create_llm_features_2026_08_05/outputs/clusters/remove/cluster_kmeans.png && echo 'remove kmeans png OK'

# Must NOT have run production yet
# (no requirement that RESULTS.md exists; if a stub exists from elsewhere, it must not claim 500/500 production)
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Smoke both classes | all eight stage outputs (4 stages × 2 classes) exist | Missing class or stage |
| Dual cluster viz | four non-empty class-root PNGs | Missing PNG / only one method |
| Labels from HDBSCAN | Stage-4 metadata / inputs reference `assignments_hdbscan` | Labels from KMeans |
| No production | no `--sample-size 500` run in this step; no production `RESULTS.md` | 500/500 or RESULTS written here |
| Approval gate | stop and wait; Step 7 only after explicit user approval | Production started without approval |
| Shared isolation | no diffs under `shared/` or `pyproject.toml` from this plan | Shared edits |

## Done when

- Tiny live smoke completed for keep and remove across all four stages.
- Dual-method cluster PNGs exist for both classes; labels use HDBSCAN.
- User has been asked to review smoke artifacts; Step 7 is blocked until explicit approval.
- README documents smoke (`--sample-size 10`) vs production (`--sample-size 500`) and the approval gate.
- Production 500/500 and `RESULTS.md` are **not** done in this step.
