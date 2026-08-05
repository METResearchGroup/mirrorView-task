# Step 3: Implement BERTopic fit (no LLM)

## Goal

Implement `experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` to run `BERTopic.fit_transform(docs, embeddings)` with Titan vectors passed in explicitly (`embedding_model=None`). Use the UMAP / HDBSCAN / CountVectorizer settings from the experiment README. Soft probabilities on. Write timestamped artifacts under `outputs/topics/original/<UTC_TS>/`. **No OpenAI / LLM calls in this stage.**

## Caller / unit of work

**Smoke caller (Step 6):**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py \
  --sample-size 50 --seed 42
```

**Production caller (Step 7 only, after smoke approval):**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py
```

(omit `--sample-size` ⇒ all rows present in the Stage-1 original embedding cache, joined back to `original_text` by `message_id`)

**In scope:** Stage-2 fit + artifact write + shared 2-D UMAP for viz.

**Out of scope:** LLM topic labels, Plotly figures, Bedrock, mirror role, `export_features.py`, `RESULTS.md`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Exact UMAP/HDBSCAN/CountVectorizer/BERTopic kwargs; artifact tree |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` | `topics_dir`, `embeddings_dir`, `new_run_timestamp` |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | Reload `original_text` by `message_id` |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` | Cache load API from Step 2 |
| BERTopic custom embeddings docs | Confirm `fit_transform(docs, embeddings)` with `embedding_model=None` |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py`
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (Stage-2 CLI)
- Runtime artifacts under `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/topics/original/`
- Optional: `/workspace/.gitignore` only if adding an ignore rule for large `outputs/topics/original/*/model/` dirs (document in README)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` (except a tiny shared read-helper extraction into `paths.py`/`data.py` if needed)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py`
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py`
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`
- Do **not** import or call `bertopic.representation.OpenAI` in this step

## Contracts

### Model construction (exact defaults from README)

```python
umap_model = UMAP(
    n_neighbors=15,
    n_components=5,
    min_dist=0.0,
    metric="cosine",
    random_state=42,
)
hdbscan_model = HDBSCAN(
    min_cluster_size=15,  # production default; see smoke override below
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
)
vectorizer_model = CountVectorizer(stop_words="english", min_df=2)

topic_model = BERTopic(
    embedding_model=None,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer_model,
    calculate_probabilities=True,
    verbose=True,
)
```

**Smoke override:** when `--sample-size 50`, set `min_cluster_size=5` (or `max(3, sample_size // 10)`) so HDBSCAN can form clusters on a tiny sample. Record the effective `min_cluster_size` in `metadata.json`. Production (no `--sample-size`) uses `15`.

### Input assembly

1. Load Stage-1 cache from `embeddings_dir("original")`. Raise `FileNotFoundError` if missing.
2. Load posts via Step-1 data helper; join `original_text` on `message_id`.
3. Build aligned `docs: list[str]` and `embeddings: np.ndarray (n, 256)` in **identical** `message_id` order.
4. If `--sample-size N`: sample `N` rows without replacement with `--seed` (default `42`), then fit only on that subset. Persist the sampled `message_id` list in metadata.
5. Call `topics, probs = topic_model.fit_transform(docs, embeddings)`.
6. Keep/remove and unanimous columns must **not** be passed into BERTopic and must not affect clustering.

### Shared 2-D UMAP for viz

Fit a separate `UMAP(n_neighbors=15, n_components=2, min_dist=0.0, metric="cosine", random_state=42)` on the same embeddings used for fit (the sampled or full matrix). Write `umap_2d.npy` with shape `(n, 2)`, row-aligned with `assignments.parquet`. Do **not** reuse the internal 5-D UMAP coordinates for the scatter plots.

### Output layout

`experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>/`

| File | Content |
|------|---------|
| `metadata.json` | `text_role`, `sample_size` (null if full), `seed`, `message_ids`, UMAP/HDBSCAN/CountVectorizer/BERTopic params, `n_docs`, `n_topics` (excluding −1), `n_noise`, `embedding_cache_path`, `model_id` of embeddings, `unanimous_rule_id` unused/null, `llm_used: false` |
| `assignments.parquet` | `message_id`, `topic`, `probability` (max soft prob if available; else null) |
| `probabilities.npy` | optional but preferred when `calculate_probabilities=True`; shape `(n, n_topics)` or BERTopic’s returned shape — document actual shape in metadata |
| `topic_info.parquet` | BERTopic `get_topic_info()` as parquet (c-TF-IDF keywords / `Name`) |
| `umap_2d.npy` | `(n, 2)` float array |
| `model/` | `topic_model.save(...)` directory |

CLI must print the new run directory path on success.

## Exact commands

### Offline wiring

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_modeling_2026_08_05.src import fit_bertopic as m
assert hasattr(m, 'main') or hasattr(m, 'run_fit_bertopic')
# Ensure OpenAI is not imported at module level for this stage
import sys
assert 'openai' not in sys.modules or True  # soft check; stronger: inspect source
src = open('experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py').read()
assert 'OpenAI' not in src and 'openai' not in src
print('fit_bertopic wiring OK')
"
```

### Smoke fit (requires Stage-1 cache)

```bash
cd /workspace

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py \
  --sample-size 50 --seed 42
```

Expect a new directory under `outputs/topics/original/<UTC_TS>/` containing at least `metadata.json`, `assignments.parquet`, `topic_info.parquet`, `umap_2d.npy`, and `model/`.

Verify:

```bash
PYTHONPATH=. uv run --extra bertopic python -c "
from pathlib import Path
import json, numpy as np, pandas as pd
root = Path('experiments/bertopic_modeling_2026_08_05/outputs/topics/original')
runs = sorted([p for p in root.iterdir() if p.is_dir()])
assert runs, 'no topics runs'
run = runs[-1]
meta = json.loads((run/'metadata.json').read_text())
assert meta.get('llm_used') is False
assert meta.get('sample_size') == 50
umap = np.load(run/'umap_2d.npy')
asn = pd.read_parquet(run/'assignments.parquet')
assert umap.shape == (len(asn), 2)
assert set(['message_id','topic']).issubset(asn.columns)
print('fit smoke artifacts OK', run)
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Embeddings passed in | `embedding_model=None`; fit uses cache vectors | BERTopic re-embeds / SentenceTransformers default |
| No LLM | no OpenAI import/use; `llm_used: false` | Representation OpenAI in this stage |
| Params | README UMAP/HDBSCAN/vectorizer values (smoke min_cluster_size override recorded) | Silent param drift |
| Artifacts | assignments + topic_info + umap_2d + model + metadata | Missing files |
| Alignment | `umap_2d` rows == assignments rows == sampled n | Shape mismatch |
| Labels unused | keep/remove / unanimous not in fit inputs | Stratified fit by label |

## Done when

- Stage 2 fits BERTopic on original docs + Titan embeddings with README params.
- Timestamped topics run written with assignments, c-TF-IDF topic info, `umap_2d.npy`, model, metadata.
- Smoke `--sample-size 50` works; production path (full corpus) is implemented but **not** required to run in this step.
- No OpenAI calls.
- README documents Stage-2 CLI including smoke override for `min_cluster_size`.
