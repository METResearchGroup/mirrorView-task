# Step 2: Implement Titan embedding cache loader

## Goal

Implement `experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` so original-text Titan vectors land in a committed local cache under `outputs/embeddings/original/`. Default path loads a complete local cache with **no** AWS calls. When the local cache is missing or incomplete, resolve vectors from the keep/remove DynamoDB+S3 identity cache (`jspsych-mirror-view-embedding-cache`). Optional `--backfill` fills rows still missing after DynamoDB via `shared.embeddings.bedrock.create_embedding` only. Drop any `message_id` still without a vector. Cache stores vectors + id index only; post text always reloads from the dataset by `message_id`.

## Caller / unit of work

**Main caller (default — prefer complete local cache):**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py
```

**Populate / refresh from DynamoDB+S3 (when local cache incomplete):**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py --refresh-from-identity-cache
```

**Optional Bedrock backfill for residuals:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py \
  --refresh-from-identity-cache --backfill
```

**Smoke subset helper (used by Step 6):** `--sample-size 50 --seed 42` may write a separate smoke cache **or** filter at fit time — prefer **filter at fit time** and keep Stage 1 writing the full-corpus cache. If `--sample-size` is implemented here, it must only affect which rows are validated/printed, not truncate the committed full cache. Document the chosen behavior in README.

**In scope:** Stage-1 loader + local cache format under `outputs/embeddings/original/`.

**Out of scope:** BERTopic fit, LLM labeling, visualization, mirror embeddings, `RESULTS.md`, edits to `shared/embeddings/bedrock.py`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Cache layout; DynamoDB+S3 reuse; filter missing |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` | `embeddings_dir("original")` |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | `load_keep_remove_posts` / posts frame |
| `/workspace/experiments/predict_keep_remove_2026_07_01/embeddings/cache_loader.py` | `load_embeddings_via_dynamodb_and_s3_with_cache` |
| `/workspace/experiments/simplified_predict_remove_2026_05_13/experiment_create_embedding_and_upload.py` | `S3_BUCKET`, `DYNAMODB_TABLE_NAME = "jspsych-mirror-view-embedding-cache"` |
| `/workspace/lib/aws/embedding_identity.py` | `embedding_identity_sha256` |
| `/workspace/shared/embeddings/bedrock.py` | `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS=256`, `normalize=True` |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py`
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (Stage-1 CLI flags)
- Runtime / committed artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/`

## Files forbidden to change

- `/workspace/shared/embeddings/bedrock.py`
- `/workspace/shared/data/**`
- `/workspace/shared/schemas.py`
- `/workspace/experiments/predict_keep_remove_2026_07_01/**` (import/reuse; do not edit)
- `/workspace/experiments/simplified_predict_remove_2026_05_13/**` (import constants; do not edit)
- `/workspace/pyproject.toml` (deps already declared in Step 1)
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`
- Do not implement Stages 2–4 in this step

## Contracts

### Local cache layout (exact)

Directory: `experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/`

| File | Content |
|------|---------|
| `embeddings.npy` | `float64` array shape `(n, 256)`, row \(i\) is Titan(`original_text`) for `index.parquet` row \(i\) |
| `index.parquet` | columns: `row_id` (0..n-1 int), `message_id` (str); one row per vector; unique `message_id` |
| `metadata.json` | see below |

`metadata.json` required keys:

```json
{
  "text_role": "original",
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimensions": 256,
  "normalize": true,
  "n_rows": "<int>",
  "source": "identity_cache" | "local_cache" | "mixed_identity_and_bedrock",
  "ddb_table": "jspsych-mirror-view-embedding-cache",
  "dropped_message_ids": ["..."],
  "backfill_message_ids": ["..."],
  "unanimous_rule_id": null
}
```

(`unanimous_rule_id` is unused at Stage 1; omit or set null.)

### Resolution order

1. Load modal posts via Step-1 helper (`message_id`, `original_text`, …). Alias `post_id = message_id` when calling the keep/remove cache loader (that API expects `post_id`).
2. If local cache exists **and** is complete for all requested `message_id`s (same model_id/dims/normalize) **and** `--refresh-from-identity-cache` is **not** set: load `embeddings.npy` + `index.parquet` only. **No** DynamoDB, S3, or Bedrock.
3. Else resolve original-text vectors via `load_embeddings_via_dynamodb_and_s3_with_cache` for role `original_text` / `TEXT_ROLE_ORIGINAL`. Reuse default bucket/table from the simplified experiment constants.
4. For any `message_id` still missing after step 3:
   - Without `--backfill`: append to `dropped_message_ids` and exclude from the matrix.
   - With `--backfill`: call `shared.embeddings.bedrock.create_embedding(original_text)` (defaults only: Titan v2, 256-d, `normalize=True`); record id in `backfill_message_ids`. On Bedrock failure, drop the row and record it in `dropped_message_ids`.
5. Write/overwrite the three cache files atomically enough for crash safety (write to temp then replace is preferred).
6. Print summary: `n_rows`, `n_dropped`, `n_backfilled`, `cache_path`.

### Alignment invariants

1. `docs` for later fit **must** be `original_text` looked up by `message_id` from the dataset — never store post text in the embedding cache.
2. Row \(i\) of `embeddings.npy` corresponds to `index.parquet` row with `row_id == i`.
3. Every kept vector length is exactly 256.
4. Do not embed `mirror_text` in v1.

### AWS credentials (when refreshing / backfilling)

In Cloud Agent env, export before AWS-touching runs:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

## Exact commands

### Offline wiring (no AWS required if local cache already present — first check imports)

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_modeling_2026_08_05.src import load_embeddings as m
from shared.embeddings.bedrock import BEDROCK_MODEL_ID, EMBEDDING_DIMENSIONS
assert BEDROCK_MODEL_ID == 'amazon.titan-embed-text-v2:0'
assert EMBEDDING_DIMENSIONS == 256
assert hasattr(m, 'main') or hasattr(m, 'run_load_embeddings')
print('load_embeddings wiring OK')
"
```

### Populate local cache (requires AWS for DynamoDB+S3 on first run)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py \
  --refresh-from-identity-cache
```

Expect:

```text
experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/embeddings.npy
experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/index.parquet
experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/metadata.json
```

with `n_rows` ≈ modal corpus size minus dropped (coverage is effectively complete per README).

### Second run must be AWS-free

```bash
# Unset AWS to prove default path is local-only (optional; or just confirm no network in logs)
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py
```

Expect: loads existing cache; metadata `source` reflects local hit; no Bedrock invokes.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Shape | `embeddings.npy` is `(n, 256)` | Wrong dims |
| Index | unique `message_id`; aligned `row_id` | Misaligned / duplicate ids |
| Default path | complete cache → no Bedrock | Bedrock on every run |
| Identity reuse | uses DynamoDB+S3 loader / table `jspsych-mirror-view-embedding-cache` | Re-embeds all posts via Bedrock by default |
| Backfill | `--backfill` only calls `shared.embeddings.bedrock.create_embedding` for residuals | Bedrock without flag / custom Bedrock client |
| Text role | original only | Mirror vectors written |
| Shared isolation | no diff under `shared/embeddings/` | Shared edits |

## Done when

- Local Titan cache exists under `outputs/embeddings/original/` with `embeddings.npy`, `index.parquet`, `metadata.json`.
- Default CLI path is local-cache-only when complete.
- Identity-cache refresh and optional Bedrock `--backfill` behave as contracted.
- Offline wiring check passes; live refresh succeeds when AWS credentials are present.
- README documents Stage-1 flags.
