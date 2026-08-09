# Step 6: Smoke both groups end-to-end (approval gate)

## Goal

Run a tiny live path through all four stages for **both** `low` and `high`. Confirm artifacts land correctly. **Stop and wait for explicit user approval** before Step 7. Do **not** run full-corpus production. Do **not** write production `RESULTS.md`.

## Caller / unit of work

Smoke size: **`--sample-size 10`**, **`--docs-per-batch 10`**, **`--seed 42`** per group → 1 feature-gen prompt each (if group has ≥10 rows).

If Stage 1 QA rejects the entire smoke batch (`features=[]`), re-run Stage 1 once with a different `--seed` (e.g. `43`) or `--sample-size 20` so Stage 2 has ≥1 feature. Document the seed actually used when reporting smoke results.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| Part 2 stage CLIs under `part_2_mine_free_responses/src/` | Commands |
| Step-3/4/5 contracts | Expected artifact trees |
| Repo-root `.env` | `OPENAI_API_KEY`; AWS creds for Bedrock |

## Files allowed to change

- Runtime artifacts only under `part_2_mine_free_responses/outputs/**`
- Optional short smoke note file **only if useful**: `part_2_mine_free_responses/SMOKE_NOTES.md` (not production RESULTS)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- Production `RESULTS.md` (do not create yet)
- Full-corpus Stage-1 runs

## Exact commands

Run from repo root. Export AWS if needed for Bedrock (local profile or `LAB_*` → standard keys per `AGENTS.md`).

### LOW

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \
  --likert-group low --sample-size 10 --docs-per-batch 10 --seed 42
# Record LOW_FEAT_DIR=.../outputs/generated_features/low/outputs/<TS>

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \
  --likert-group low

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \
  --likert-group low --seed 42

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py \
  --likert-group low --sample-per-cluster 8 --seed 42
```

### HIGH

Same four commands with `--likert-group high`.

### Pass checklist (must all hold)

1. Stage-1 dirs exist for low and high under `outputs/generated_features/{group}/outputs/`.
2. Stage-2 dirs exist with `embeddings.npy` + `features.jsonl` + `feature_ids.json`.
3. Stage-3 dirs exist with both assignment JSONs; class-root PNGs exist:
   - `outputs/clusters/low/cluster_hdbscan.png`
   - `outputs/clusters/low/cluster_kmeans.png`
   - `outputs/clusters/high/cluster_hdbscan.png`
   - `outputs/clusters/high/cluster_kmeans.png`
4. Stage-4 dirs exist under `outputs/generated_labels/{low,high}/outputs/` with rows only for non-noise HDBSCAN clusters (or explicitly zero non-noise clusters documented for tiny smoke).
5. Operator reports smoke artifact paths to the user and **stops**.

### Fail criteria

- Starts Step-7 production without explicit approval
- Writes production `RESULTS.md` in this step
- Edits parent README
- Skips one of the two groups

## Approval gate

**Do not start Step 7 until the user explicitly approves after reviewing the smoke artifacts (including the four class-root cluster PNGs and sample Stage-1/4 JSON).**

## Done when

1. Both groups completed Stages 1–4 at smoke size.
2. Pass checklist items 1–5 verified.
3. Conversation waits on user approval (no production run yet).
