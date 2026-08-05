# Creating LLM-based features

## Purpose

Our goal here is to extract features using an LLM.

## Approach

We'll split the data between the posts that were kept and the posts that were removed. We have a data loader that manages this for us.

For each, the approach is something like:

1. Give an LLM bunches of documents all at once and then ask it to generate features.
2. Get a semantic embedding of each generated feature.
3. Cluster the semantic embeddings.
4. Ask a language model to give a name/label for each cluster, by giving it a random sample of documents from the cluster.

We'll run this in a pipeline-like approach.

We have the following Python files, in src/

- llm_generate_features.py # uses the `runner` from research_tools
- generate_embeddings.py
- cluster_embeddings.py
- generate_labels_for_embeddings.py # uses the `runner` from research_tools

We store our results in outputs/, as

- generated_features/{keep,remove}
- generated_embeddings/{keep,remove}
- clusters/{keep,remove}
- generated_labels/{keep,remove}

We keep all generated outputs in this folder.

We use `gpt5.4-nano` for our LLM. We use Amazon Titan for the embeddings (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized). Note: this experiment embeds *feature* texts, not posts. Shared Titan post embeddings from the prior keep/remove pipeline (DynamoDB+S3 identity cache) are already available for reuse elsewhere (e.g. BERTopic); any missing post vectors can be filtered out without affecting generality.

This repo has the following setup:

- README.md
- RESULTS.md
- src/
  - llm_generate_features.py
  - generate_embeddings.py
  - cluster_embeddings.py
  - generate_labels_for_embeddings.py
- outputs/
  - generated_features/{keep,remove}
  - generated_embeddings/{keep,remove}
  - clusters/{keep,remove}
  - generated_labels/{keep,remove}

## Stage run order

Per label class: `keep` | `remove`. Stages are class-conditional (never mix keep and remove in one LLM batch).

Pinned sizes:

- Smoke (Step 6): `--sample-size 10 --posts-per-batch 10` → 1 feature-gen prompt/class, ≤8 features/prompt
- Production (Step 7, **only after explicit smoke approval**): `--sample-size 500 --posts-per-batch 10` → 50 keep + 50 remove feature-gen prompts; ≤8 features/prompt → ≤800 features to embed
- Clustering (Stage 3): both HDBSCAN + KMeans; PNGs at `outputs/clusters/{keep,remove}/cluster_{hdbscan,kmeans}.png`
- Labeling (Stage 4): **HDBSCAN assignments only** (KMeans is comparison-only). Noise (`cluster_id=-1`) is skipped for labeling.
- HDBSCAN `min_cluster_size` defaults to 5; for tiny smoke `n` it is auto-lowered (documented in Stage-3 metadata).

Requires `OPENAI_API_KEY` (repo-root `.env` or env) and AWS credentials for Bedrock Titan.

### Smoke (both classes)

```bash
# --- KEEP ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep --sample-size 10 --posts-per-batch 10 --seed 42
# Record KEEP_FEAT_DIR=.../outputs/generated_features/keep/outputs/<TS>
# Or omit --features-run-dir below to use latest timestamp

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep --features-run-dir "$KEEP_FEAT_DIR"

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep --embeddings-run-dir "$KEEP_EMB_DIR" --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep --clusters-run-dir "$KEEP_CLUS_DIR" --sample-per-cluster 8 --seed 42

# --- REMOVE ---
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class remove --sample-size 10 --posts-per-batch 10 --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class remove --features-run-dir "$REMOVE_FEAT_DIR"

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class remove --embeddings-run-dir "$REMOVE_EMB_DIR" --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class remove --clusters-run-dir "$REMOVE_CLUS_DIR" --sample-per-cluster 8 --seed 42
```

Stages 2–4 also accept omitting the `*-run-dir` flag to use the latest timestamp under that class’s stage root.

### Production (after smoke approval only)

```bash
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep --sample-size 500 --posts-per-batch 10 --seed 42
# → 50 prompts; leftover_message_ids empty

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class keep

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class keep --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class keep --sample-per-cluster 8 --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class remove --sample-size 500 --posts-per-batch 10 --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \
  --label-class remove

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py \
  --label-class remove --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \
  --label-class remove --sample-per-cluster 8 --seed 42
```

Do **not** run production until smoke artifacts (including the four class-root cluster PNGs) are reviewed and explicitly approved. Write `RESULTS.md` only from the production run.

### Artifact formats

| Stage | Primary artifacts |
|-------|-------------------|
| 1 | `outputs/generated_features/{class}/outputs/{ts}/` (runner `metadata.json` + item JSON) |
| 2 | `outputs/generated_embeddings/{class}/{ts}/features.jsonl` + `embeddings.npy` + `feature_ids.json` |
| 3 | `outputs/clusters/{class}/{ts}/assignments_hdbscan.json` (+ `assignments_kmeans.json`); class-root PNGs |
| 4 | `outputs/generated_labels/{class}/outputs/{ts}/` (runner rows with `result.cluster_label`) |
