# Step 7: Production run (full low + full high) and RESULTS.md

## Goal

Only after **explicit Step-6 smoke approval**: run Stages 1–4 on the **full** low and **full** high corpora (all usable reflection + Likert rows in each group), then write `part_2_mine_free_responses/RESULTS.md` summarizing the production outcomes.

## Precondition

User has explicitly approved Step-6 smoke. If not, stop — do not run this step.

## Caller / unit of work

**Pinned production settings:**

| Setting | Value |
|---------|-------|
| Groups | all `low` + all `high` |
| Docs per feature-gen batch | **10** |
| Max features per prompt | **8** |
| Seed | **42** |
| LLM | `gpt-5.4-nano` |
| Embeddings | Titan v2 256-d L2 via shared (`amazon.titan-embed-text-v2:0`) |
| Clustering | HDBSCAN + KMeans; labels from **HDBSCAN** only |
| Sample size | full group (`--sample-size` ≥ group n, or a dedicated `--all` flag if implemented) |

Expected approximate n: low ~255 → 25 full batches + 5 leftovers; high ~922 → 92 full batches + 2 leftovers. Leftovers recorded, not sent to LLM.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/RESULTS.md` | RESULTS.md structure to mirror (adapt keep/remove → low/high) |
| Step-6 smoke artifact paths | Confirm approval context |
| Part 2 stage CLIs | Production commands |

## Files allowed to change

- Runtime production artifacts under `part_2_mine_free_responses/outputs/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/RESULTS.md` (create/overwrite from **this** production run only)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- Part 1 histogram outputs

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# --- LOW (full corpus) ---
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \
  --likert-group low --sample-size 100000 --docs-per-batch 10 --seed 42

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \
  --likert-group low

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \
  --likert-group low --seed 42

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py \
  --likert-group low --sample-per-cluster 8 --seed 42

# --- HIGH (full corpus) ---
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \
  --likert-group high --sample-size 100000 --docs-per-batch 10 --seed 42

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \
  --likert-group high

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \
  --likert-group high --seed 42

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py \
  --likert-group high --sample-per-cluster 8 --seed 42
```

(`--sample-size 100000` is a “≥ group size ⇒ use all” convention matching keep/remove behavior; if Step 3 implemented an explicit `--all` flag, use that instead and document it in RESULTS.)

## RESULTS.md required contents

Write `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/RESULTS.md` with:

1. Date, seed, smoke-approval note, production = full low + full high.
2. Budget table: n low, n high, batches sent, leftovers, features embedded (actual), QA-rejected batch count if available from Stage-1 metadata/rows.
3. Models/methods: `gpt-5.4-nano`, Titan config, HDBSCAN as labeling source, noise policy.
4. Class-root PNG paths for low and high (both methods).
5. Per-group tables: n sampled, feature-gen batches, features embedded, HDBSCAN cluster count (excl. noise), noise count, KMeans \(k\), stage timestamp paths.
6. Per-group HDBSCAN label tables: `cluster_id`, `n_members`, `cluster_label`, `definition`.

## Pass / fail

### Pass

- Full low and high Stage-1–4 complete without crashing.
- `RESULTS.md` exists and matches the production artifact paths (not smoke paths).
- Parent README untouched.

### Fail

- Production run without Step-6 approval
- RESULTS written from smoke-only artifacts
- Parent README edited
- Only one group run

## Done when

1. Production artifacts for both groups exist under Part 2 `outputs/`.
2. `part_2_mine_free_responses/RESULTS.md` documents the full-corpus labeled clusters.
3. Plan “What done looks like” items 1–7 in `plan.md` are satisfied.
