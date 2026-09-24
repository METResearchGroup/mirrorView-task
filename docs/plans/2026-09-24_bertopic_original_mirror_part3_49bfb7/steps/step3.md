# Step 3: Backfill and cache Titan and MiniLM embeddings

## Goal

Populate Titan Text Embeddings V2 (256-d, L2-normalized) caches for **both** text roles over all **18,899** stimulus posts. Embed **before** dedupe. Reuse the DynamoDB+S3 identity cache (`jspsych-mirror-view-embedding-cache`) with Bedrock backfill for misses (~20k texts across both roles). Hard fail if coverage is below 100%. Build local `all-MiniLM-L6-v2` caches under `outputs/embeddings_minilm/{original,mirror}/` in this step (feeds ablation A3 in Step 7; not deferred).

## Caller / unit of work

**Titan original role (identity refresh + backfill):**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \
  --text-role original --refresh-from-identity-cache --backfill
```

**Titan mirror role:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \
  --text-role mirror --refresh-from-identity-cache --backfill
```

**MiniLM both roles:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py --text-role original

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py --text-role mirror
```

**In scope:** `load_embeddings.py`, `load_embeddings_minilm.py`, `data.py` helpers if needed, experiment `.gitignore` rules, README/SETUP CLI notes, S3 upload of large embedding caches after build, optional `pyproject.toml` bertopic extra pin for `sentence-transformers`.

**Out of scope:** BERTopic fit, dedupe at embed time, LLM labeling, visualization, bulk upload of topics/models (Step 8).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` | Titan cache layout and identity resolution |
| `/workspace/experiments/predict_keep_remove_2026_07_01/embeddings/cache_loader.py` | DynamoDB+S3 loader |
| `/workspace/experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` | `TEXT_ROLE_ORIGINAL`, `TEXT_ROLE_MIRROR` |
| `/workspace/shared/embeddings/bedrock.py` | `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS=256` |
| `/workspace/lib/aws/embedding_identity.py` | `embedding_identity_sha256` |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/data.py` | `load_stimuli_posts()` (18,899 rows) |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/paths.py` | `embeddings_dir`, `embeddings_minilm_dir` |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` | Step 2 S3-primary patterns |
| `/workspace/AGENTS.md` | AWS env export; err on S3 for larger files |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/data.py` (only if a thin `load_stimuli_for_embedding()` helper is needed)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (Stage 1 CLI flags)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/SETUP.md` (embedding cache section)
- `/workspace/pyproject.toml` (only `[project.optional-dependencies].bertopic`: add `sentence-transformers>=3.0.0` if import fails)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` (extend Step 2 patterns if needed)
- Runtime artifacts under `experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/` and `outputs/embeddings_minilm/` (`index.parquet` and `metadata.json` committed; `embeddings.npy` S3-primary)

## Files forbidden to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/**`
- `/workspace/shared/embeddings/bedrock.py`
- `/workspace/shared/data/**`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/dedupe.py` (dedupe is fit-time only)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py`
- Any other file

## Implementation details

### Corpus for embedding (critical)

- Load via `data.load_stimuli_posts()` -> **18,899** rows (full stimuli, **not** deduped, **not** keep/remove labels).
- `post_id` is the cache index key (renamed from `post_primary_key`).
- Text by `--text-role`:
  - `original` -> column `original_text`
  - `mirror` -> column `mirror_text`
- Identity-cache lookup hashes the **exact** text string with Titan defaults (`amazon.titan-embed-text-v2:0`, 256-d, `normalize=True`). Mirror role must hash `mirror_text`, not `mirrored_text` column name (already renamed in `data.py`).

### `load_embeddings.py` (Titan)

Port Part 2 resolver with these Part 3 changes:

| Setting | Value |
|---------|-------|
| `N_EXPECTED = 18899` | Hard requirement |
| `TEXT_ROLES` | `original`, `mirror` only (no `joint` in this module) |
| Coverage rule | **Hard fail** if `n_rows != N_EXPECTED` or any `dropped_post_ids` when `--backfill` is set |
| Default without flags | Load complete local cache if valid; no AWS |
| `--refresh-from-identity-cache` | Rebuild from DynamoDB+S3 |
| `--backfill` | Bedrock `create_embedding(text)` for misses after identity lookup |
| `--text-role` | Required; `original` or `mirror` |

**Per-role cache directory:** `paths.embeddings_dir(role)` -> `outputs/embeddings/{original,mirror}/`

| File | Content |
|------|---------|
| `embeddings.npy` | `float64` shape `(18899, 256)` |
| `index.parquet` | columns: `row_id` (0..18898 int), `post_id` (str); unique `post_id`; sorted by `post_id` ascending |
| `metadata.json` | see below |

**`metadata.json` required keys:**

```json
{
  "text_role": "original" | "mirror",
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimensions": 256,
  "normalize": true,
  "n_rows": 18899,
  "n_expected": 18899,
  "source": "local_cache" | "identity_cache" | "mixed_identity_and_bedrock",
  "ddb_table": "jspsych-mirror-view-embedding-cache",
  "dropped_post_ids": [],
  "backfill_post_ids": ["..."],
  "corpus": "study_phase_2_part_3_stimuli_full",
  "dedupe_applied": false
}
```

On incomplete coverage after backfill:

```python
raise RuntimeError(
    f"Titan embedding coverage {n_rows}/{N_EXPECTED} for role={role}; "
    f"dropped={dropped_post_ids[:5]}"
)
```

Disk scratch for identity downloads: `outputs/embeddings/.identity_disk_cache/` (gitignored).

Print on success:

```text
n_rows=18899 n_expected=18899 n_backfilled=<int> source=<str> cache_path=<path>
```

### `load_embeddings_minilm.py` (ablation A3)

| Setting | Value |
|---------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` via `SentenceTransformer` |
| Dimensions | 384 (model default; L2-normalize vectors before save) |
| Corpus | Same 18,899 `load_stimuli_posts()` frame |
| Coverage | Hard fail if `n_rows != 18899` |
| Network | May download model weights on first run (no Bedrock) |

**Per-role cache directory:** `paths.embeddings_minilm_dir(role)` -> `outputs/embeddings_minilm/{original,mirror}/`

Same three-file layout as Titan (`embeddings.npy`, `index.parquet`, `metadata.json`) with:

```json
{
  "text_role": "original" | "mirror",
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "dimensions": 384,
  "normalize": true,
  "n_rows": 18899,
  "n_expected": 18899,
  "source": "local_compute",
  "corpus": "study_phase_2_part_3_stimuli_full",
  "dedupe_applied": false
}
```

CLI: `--text-role {original,mirror}` required. No `--backfill` (local compute only).

### Alignment invariants (both backends)

1. Row `i` of `embeddings.npy` matches `index.parquet` row where `row_id == i`.
2. Post text is **not** stored in the cache; reload from `load_stimuli_posts()` by `post_id`.
3. Caches are keyed on full 18,899 stimuli so dedupe in Step 4 can subset by `post_id` without re-embedding.

### Gitignore vs committed vs S3

Use `experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` from Step 2. Do not add Part 3 patterns to the repo root `.gitignore`.

| Path | Git | S3 |
|------|-----|-----|
| `outputs/embeddings/{original,mirror}/embeddings.npy` | **Gitignored** (S3-primary) | Upload after build (this step) |
| `outputs/embeddings/{original,mirror}/index.parquet` | Committed | Upload (Step 8) |
| `outputs/embeddings/{original,mirror}/metadata.json` | Committed | Upload (Step 8) |
| `outputs/embeddings/.identity_disk_cache/` | **Gitignored** | Do not upload |
| `outputs/embeddings_minilm/{original,mirror}/embeddings.npy` | **Gitignored** (S3-primary) | Upload after build (this step) |
| `outputs/embeddings_minilm/{original,mirror}/index.parquet` | Committed | Upload (Step 8) |
| `outputs/embeddings_minilm/{original,mirror}/metadata.json` | Committed | Upload (Step 8) |
| `outputs/topics/**` | Not created this step | N/A |

S3 bucket: `mirrorview-experimental-artifacts`  
S3 prefix: `experiments/bertopic_original_mirror_part3_2026_09_24/` (same relative paths as local)

**Upload large caches after build** (run once per role after Titan and MiniLM caches pass verification):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for ROLE in original mirror; do
  aws s3 cp \
    experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/${ROLE}/embeddings.npy \
    s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/${ROLE}/embeddings.npy
  aws s3 cp \
    experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings_minilm/${ROLE}/embeddings.npy \
    s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings_minilm/${ROLE}/embeddings.npy
done
```

**Pull from S3 if missing (Steps 4+):** On fresh clones, download `embeddings.npy` before fit or analysis if the local file is absent:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for ROLE in original mirror; do
  LOCAL=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/${ROLE}/embeddings.npy
  if [ ! -f "$LOCAL" ]; then
    aws s3 cp s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/${ROLE}/embeddings.npy "$LOCAL"
  fi
done
```

Repeat for `outputs/embeddings_minilm/{original,mirror}/embeddings.npy` when Step 7 ablations need MiniLM caches. Keep `index.parquet` and `metadata.json` in git so row alignment stays versioned locally.

## TDD tests to write first

Add to `experiments/bertopic_original_mirror_part3_2026_09_24/tests/`:

### `test_load_embeddings.py`

| Test name | Given | Assert |
|-----------|-------|--------|
| `test_select_text_for_role_original` | Stimuli row | Titan input text equals `original_text` |
| `test_select_text_for_role_mirror` | Stimuli row | Titan input text equals `mirror_text` |
| `test_write_cache_metadata_schema` | Mocked 2-row resolve | `metadata.json` keys present; `n_expected` set |
| `test_hard_fail_on_incomplete_coverage` | Resolver returns 1 of 2 ids | `RuntimeError` with `coverage` in message |
| `test_index_sorted_by_post_id` | Mocked write | `index.parquet` sorted ascending |

Use mocks for DynamoDB/S3/Bedrock in unit tests. Do not call AWS in unit tests.

### `test_load_embeddings_minilm.py`

| Test name | Assert |
|-----------|--------|
| `test_minilm_metadata_dimensions_384` | metadata `dimensions == 384` |
| `test_minilm_normalize_vectors` | Row L2 norms ~1.0 |
| `test_minilm_hard_fail_incomplete` | Missing row raises `RuntimeError` |

## Exact commands

```bash
cd /workspace
uv sync --extra bertopic

# Unit tests (mocked; expect FAIL then PASS)
PYTHONPATH=. uv run pytest \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_load_embeddings.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_load_embeddings_minilm.py \
  -v

# Live Titan backfill (requires AWS)
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \
  --text-role original --refresh-from-identity-cache --backfill

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \
  --text-role mirror --refresh-from-identity-cache --backfill
```

Expected per-role stdout:

```text
n_rows=18899 n_expected=18899 n_backfilled=<int> source=mixed_identity_and_bedrock cache_path=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/original
```

Verification:

```bash
PYTHONPATH=. uv run --extra bertopic python -c "
import json, numpy as np, pandas as pd
from pathlib import Path
root = Path('experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings')
for role in ('original','mirror'):
    d = root / role
    meta = json.loads((d/'metadata.json').read_text())
    emb = np.load(d/'embeddings.npy')
    idx = pd.read_parquet(d/'index.parquet')
    assert meta['n_rows'] == meta['n_expected'] == 18899
    assert meta['dedupe_applied'] is False
    assert len(meta['dropped_post_ids']) == 0
    assert emb.shape == (18899, 256)
    assert len(idx) == 18899
    assert idx['post_id'].is_unique
print('titan caches OK')
"

# MiniLM (no AWS)
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py --text-role original

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py --text-role mirror

PYTHONPATH=. uv run --extra bertopic python -c "
import json, numpy as np, pandas as pd
from pathlib import Path
root = Path('experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings_minilm')
for role in ('original','mirror'):
    d = root / role
    meta = json.loads((d/'metadata.json').read_text())
    emb = np.load(d/'embeddings.npy')
    assert meta['n_rows'] == 18899
    assert emb.shape == (18899, 384)
print('minilm caches OK')
"

# Second Titan run must be AWS-free when caches complete
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py --text-role original
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Corpus size | Exactly 18,899 per role per backend | Deduped count or rated-only count |
| Titan shape | `(18899, 256)` both roles | Any drop without hard fail |
| MiniLM shape | `(18899, 384)` both roles | Missing role folder |
| Coverage | `dropped_post_ids == []` and `n_rows == n_expected` | Silent drops (Part 2 behavior) |
| Pre-dedupe | `metadata.dedupe_applied == false` | Dedupe before embed |
| Identity reuse | DynamoDB table `jspsych-mirror-view-embedding-cache` | Bedrock-only default |
| AWS | Export `LAB_*` to `AWS_*` before live backfill | Unset credentials |
| S3 upload | All four `embeddings.npy` files on S3 after build | Large arrays committed to git only |
| Part 2 isolation | No diff under `experiments/bertopic_modeling_2026_08_05/` | Any change |
| Tests | Mocked unit tests green | AWS required for pytest |

## Commit message(s)

```
Add Part 3 Titan and MiniLM embedding caches for both roles

Implement load_embeddings and load_embeddings_minilm over all 18,899
stimulus posts with identity-cache lookup, Bedrock backfill, and 100%
coverage enforcement. Gitignore large embedding arrays; upload them to S3
after build. Add unit tests.
```
