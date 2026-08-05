# Step 3: Embed generated features with Titan

## Goal

Implement `experiments/create_llm_features_2026_08_05/src/generate_embeddings.py` to read Stage-1 feature texts for one label class, call `shared.embeddings.bedrock.create_embedding` (Amazon Titan Text Embeddings V2, 256-d, L2-normalized), and write vectors plus provenance under `outputs/generated_embeddings/{keep,remove}/`.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep \
  --features-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/<TIMESTAMP>
```

(`--features-run-dir` may default to the latest timestamp directory under `stage1_root(label_class)/outputs/` if that convenience is implemented; if implemented, document it in README.)

**In scope:** Stage-2 embedding script only.

**Out of scope:** clustering, cluster labeling, re-running Stage 1, editing `shared/embeddings/bedrock.py`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/shared/embeddings/bedrock.py` | `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS=256`, `normalize=True` default |
| `/Users/mark/src/work/mirrorView-task/shared/embeddings/__init__.py` | Public exports |
| Stage-1 output JSON under `outputs/generated_features/{keep,remove}/outputs/{ts}/` | Feature row shape (`result.features[]`) |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/paths.py` (or `data.py`) | `stage2_root` |
| `/Users/mark/src/work/mirrorView-task/pyproject.toml` | Confirm `boto3` is in the `dev` group (`uv sync` installs `dev` by default per AGENTS.md) |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/generate_embeddings.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (Stage-2 CLI)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/{keep,remove}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/embeddings/bedrock.py`
- `/Users/mark/src/work/mirrorView-task/shared/schemas.py`
- `/Users/mark/src/work/mirrorView-task/shared/data/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` (except if a tiny shared helper was wrongly placed there — prefer not to touch)
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`

## Contracts

### Input

1. Resolve Stage-1 run directory for `--label-class` (explicit `--features-run-dir` or latest `*/outputs/{ts}` under stage1 root).
2. Load every `*.json` except `metadata.json`.
3. For each row, iterate `result["features"]` (list). Skip rows with missing/empty `features`.
4. Build embedding input text exactly:

   ```text
   {feature_name}: {feature_value}. {rationale}
   ```

   Strip surrounding whitespace. Raise `ValueError` if the resulting string is empty after strip.
5. Assign a stable `feature_id` per feature within the run, e.g. `{batch_id}_{index_in_batch}` or `{message_id}::{feature_name}::{index}` — pick one scheme and write it in metadata. Prefer uniqueness within the run.

### Embedding call

```python
from shared.embeddings.bedrock import (
    create_embedding,
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)

out = create_embedding(text)  # defaults: titan v2, 256-d, normalize=True
assert out["model_id"] == BEDROCK_MODEL_ID
assert out["dimensions"] == EMBEDDING_DIMENSIONS
assert out["normalize"] is True
assert len(out["embedding"]) == 256
```

Do **not** pass alternate `model_id` / `dimensions` / `normalize=False`.

Requires AWS credentials that can call Bedrock in `us-east-1` (see `shared/embeddings/bedrock.py` `AWS_REGION`).

### Output layout (no research_tools runner)

Write under `stage2_root(label_class) / {run_timestamp}/` where `run_timestamp` is created at Stage-2 start (ISO-like local stamp is fine; be consistent with other stages):

| File | Content |
|------|---------|
| `metadata.json` | `label_class`, `source_features_run_dir`, `model_id`, `dimensions`, `normalize`, `n_features`, `seed` (if any), feature_id scheme |
| `features.jsonl` **or** `embeddings.json` | One record per feature: `feature_id`, `message_id`, `feature_name`, `feature_value`, `category`, `rationale`, `evidence_span`, `text_embedded`, `embedding` (list[float] len 256), `input_text_token_count` |
| `embeddings.npy` (optional but preferred) | `float64` array shape `(n_features, 256)` row-aligned with a sidecar `feature_ids.json` list |

Pin one primary format in the implementation and document it in README. Downstream Stage 3 must load that format only.

Progress: print or tqdm over features as each Bedrock call completes.

## Exact commands

### Offline import check

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from shared.embeddings.bedrock import create_embedding, BEDROCK_MODEL_ID, EMBEDDING_DIMENSIONS
from experiments.create_llm_features_2026_08_05.src import generate_embeddings as m
assert BEDROCK_MODEL_ID == 'amazon.titan-embed-text-v2:0'
assert EMBEDDING_DIMENSIONS == 256
assert hasattr(m, 'main') or hasattr(m, 'run_generate_embeddings')
print('embed wiring OK')
"
```

### Live embed (requires AWS + prior Stage-1 smoke artifacts)

```bash
cd /Users/mark/src/work/mirrorView-task

# Replace TIMESTAMP with the Stage-1 keep run folder name
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep \
  --features-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/TIMESTAMP

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class remove \
  --features-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_features/remove/outputs/TIMESTAMP
```

Expect directories under:

- `experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/keep/<stage2_ts>/`
- `experiments/create_llm_features_2026_08_05/outputs/generated_embeddings/remove/<stage2_ts>/`

with `metadata.json` showing `dimensions: 256` and `model_id: amazon.titan-embed-text-v2:0`.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Shared helper | imports `create_embedding` from `shared.embeddings.bedrock` | Reimplements Bedrock client locally |
| Dim / normalize | every vector length 256; metadata `normalize: true` | Other dims / `normalize: false` |
| Provenance | each row retains `message_id` + feature fields + `text_embedded` | Vectors only, no lineage |
| Paths | writes under `outputs/generated_embeddings/{keep,remove}/` | Writes into Stage-1 tree or shared |
| No shared edit | `git diff -- shared/embeddings/bedrock.py` empty | Diff present |

## Done when

- Stage 2 embeds Stage-1 **features** (not raw posts) via Titan v2 256-d L2-normalized.
- Artifacts for keep and remove land under `outputs/generated_embeddings/{keep,remove}/`.
- Offline wiring check passes; live embed succeeds when AWS credentials and Stage-1 artifacts exist.
