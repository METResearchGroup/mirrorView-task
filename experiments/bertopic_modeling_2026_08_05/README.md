# BERTopic modeling

## Purpose

Our goal here is to use BERTopic in order to generate features for the posts.

## Approach

The steps for BERTopic, at a high level, are:

1. Embed each document into a vector
2. Reduce dimensionality (default is UMAP)
3. Cluster the reduced embeddings (default is HDBSCAN)
4. For each topic (cluster), build a representation of what it is "about"
   - Default: c-TF-IDF over the documents in that topic -> ranked keywords
   - Optional: KeyBERT-style keywords, MMR diversification, LLM labels, etc.
5. Return topic assignments + topic representations

For our use case, we run BERTopic on the original post embeddings. We reuse existing Titan post embeddings from the prior keep/remove embedding pipeline (`experiments/predict_keep_remove_2026_07_01/`) via the DynamoDB+S3 identity cache (`jspsych-mirror-view-embedding-cache`). Any posts missing a cached vector are filtered out, which is OK as we've already embedded all the posts. Later work will replicate this but for the mirrored post embeddings. We fit on all the posts.

Later on, we then visualize the post clusters on a 2-D cluster map. We'll create three sets of visualizations:

- By cluster
- By cluster, but coloring each post on whether it was kept (green) or removed (red)
- By cluster, but coloring each post on whether the labels were unanimous (green) or not unanimous (red). This requires a merge with the `STUDY_PHASE_2_PART_2_RESULTS_FULL` dataset from the shared dataloader.

For the topic representation step, we'll use two methods:

- The default c-TF-IDF, to get keywords
- LLM-based labeling.

We have the following Python files, in src/:

- load_embeddings.py
- ...

We have a local cache, under `outputs/embeddings/{original,mirror}/`, that we commit to GitHub, containing the embeddings themselves.

Our pipeline looks something like this:

```python
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN  # or sklearn HDBSCAN — see dependency note below
from sklearn.feature_extraction.text import CountVectorizer

umap_model = UMAP(
    n_neighbors=15,
    n_components=5,
    min_dist=0.0,
    metric="cosine",  # good for L2-normalized Titan
    random_state=42,
)
hdbscan_model = HDBSCAN(
    min_cluster_size=15,  # tune to n_posts
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
)
vectorizer_model = CountVectorizer(stop_words="english", min_df=2)

topic_model = BERTopic(
    embedding_model=None,  # explicit: we bring vectors
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer_model,
    calculate_probabilities=True,  # soft features for downstream models
    verbose=True,
)

topics, probs = topic_model.fit_transform(docs, embeddings)
```

For generating topics with the LLM, we'll do something like this:

```python
from bertopic.representation import OpenAI
import openai

client = openai.OpenAI()  # OPENAI_API_KEY from .env
representation_model = OpenAI(
    client,
    model="gpt-5.4-nano",  # align with create_llm_features
    chat=True,
    nr_docs=4,
    diversity=0.1,
    doc_length=150,
    tokenizer="whitespace",
    prompt="""I have a topic that contains the following documents:
[DOCUMENTS]
The topic is described by the following keywords: [KEYWORDS]

Based on the information above, extract a short topic label in the following format:
topic: <topic label>
""",
)

# After fit: update representations without re-clustering
topic_model.update_topics(docs, representation_model=representation_model)
# or multi-aspect at fit time:
# BERTopic(representation_model={"ctfidf_keywords": ..., "llm": representation_model})
```

## Pipeline stages

Run as four separate scripts so clustering can be retuned without burning LLM calls:

1. **`load_embeddings.py`** — load posts + resolve Titan vectors from the identity cache into `outputs/embeddings/` (or load that local cache if already complete). Drop any posts still missing a vector. Default path should not call Bedrock once the cache exists; optional `--backfill` for missing rows only.
2. **`fit_bertopic.py`** — `fit_transform(docs, embeddings)` with `embedding_model=None`. Writes topic assignments, c-TF-IDF topic info, optional soft probabilities, saved model, and a shared 2-D UMAP for viz. No LLM in this stage.
3. **`label_topics_llm.py`** — post-hoc `update_topics` with `bertopic.representation.OpenAI` ([LLM & Generative AI](https://maartengr.github.io/BERTopic/getting_started/representation/llm.html)). Labels use keywords + a few representative docs per topic only. Skip topic `-1` (HDBSCAN noise).
4. **`visualize_clusters.py`** — one 2-D projection, three color overlays (topic / keep-remove / unanimous).

Optional later: `export_features.py` to turn topic ids / soft probs into downstream ML features.

## Data

| Need | Source |
|------|--------|
| Post texts + modal keep/remove | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader` (`message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`) |
| Unanimous vs not | Join from `STUDY_PHASE_2_PART_2_RESULTS_FULL` (linked-fate keep/remove trials aggregated per `post_id` / `message_id`). Exact rule (e.g. all raters same decision) recorded in run `metadata.json`. |
| Embeddings | Reused Amazon Titan Text Embeddings V2 (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized) from the keep/remove DynamoDB/S3 identity cache into `outputs/embeddings/`; posts without a vector are filtered out |

v1 fits on **all** posts for the **original** text role. Mirror is the same pipeline under `mirror/` later. Keep/remove and unanimous labels are for visualization only — they are not used when fitting BERTopic.

## Precomputed embeddings

Pass Titan vectors explicitly so BERTopic does not re-embed ([Custom Embeddings](https://maartengr.github.io/BERTopic/getting_started/embeddings/embeddings.html)):

```python
topics, probs = topic_model.fit_transform(docs, embeddings)
```

- Prefer the existing post Titan cache (keep/remove pipeline / DynamoDB+S3); write into `outputs/embeddings/{original,mirror}/` and skip Bedrock when the local cache is already complete.
- Filter out any `message_id` without a vector. Coverage is effectively complete, so dropping those rows does not change how general the results are.
- `docs` must be `original_text` when `embeddings` are Titan(`original_text`) — row-aligned by `message_id`.
- For any later `transform` on new posts, pass embeddings again (or set an `embedding_model`); with `embedding_model=None`, omitting embeddings will fail or pull a default model.
- Cache stores vectors + id index only; reload post text from the dataset by `message_id`.

## LLM topic labels

See [6B. LLM & Generative AI](https://maartengr.github.io/BERTopic/getting_started/representation/llm.html).

- Prefer **fit first, label second** (`update_topics`) so UMAP/HDBSCAN params can change without re-calling the API.
- Prompt tags: `[DOCUMENTS]` (top representative docs) and `[KEYWORDS]` (c-TF-IDF). Keep the trailing `topic: <topic label>` line so BERTopic’s OpenAI parser can extract the label cleanly.
- Useful knobs already in the Approach snippet: `nr_docs`, `diversity`, `doc_length`, `tokenizer`.
- Model: `gpt-5.4-nano`

## Visualizations

Reuse a single `(n, 2)` UMAP written at fit time (`umap_2d.npy`), then recolor:

1. By topic id
2. Keep (green) / remove (red) from modal labels
3. Unanimous (green) / not unanimous (red) from the results join

Emit both interactive HTML (e.g. Plotly) and PNG copies for `RESULTS.md`.

## File structure

```text
experiments/bertopic_modeling_2026_08_05/
├── README.md
├── RESULTS.md
├── src/
│   ├── paths.py                 # experiment roots; role = original | mirror
│   ├── data.py                  # KEEP_REMOVE_LABELS + unanimous join from RESULTS_FULL
│   ├── load_embeddings.py
│   ├── fit_bertopic.py
│   ├── label_topics_llm.py
│   └── visualize_clusters.py
└── outputs/
    ├── embeddings/              # committed local Titan cache
    │   ├── original/
    │   │   ├── embeddings.npy   # (n, 256)
    │   │   ├── index.parquet    # row_id, message_id
    │   │   └── metadata.json
    │   └── mirror/              # later
    ├── topics/
    │   └── original/
    │       └── <UTC_TS>/
    │           ├── metadata.json
    │           ├── assignments.parquet   # message_id, topic, probability
    │           ├── probabilities.npy     # optional soft probs
    │           ├── topic_info.parquet    # c-TF-IDF keywords / names
    │           ├── umap_2d.npy
    │           └── model/                # topic_model.save(...)
    ├── labels/
    │   └── original/
    │       └── <UTC_TS>/
    │           ├── metadata.json         # model, prompt, source_topics_run
    │           ├── topic_labels.parquet  # topic_id, ctfidf_name, llm_label, n_docs
    │           └── prompts.jsonl         # optional audit
    └── figures/
        └── original/
            └── <UTC_TS>/
                ├── clusters_by_topic.{html,png}
                ├── clusters_by_keep_remove.{html,png}
                └── clusters_by_unanimous.{html,png}
```

Prefer `parquet` / `json` / `npy` over `csv` for artifacts we commit. OK to gitignore large `models/` dirs. Assignments, topic tables, embedding cache, and figures are the important reproducible artifacts.

## Dependencies

- Add `bertopic` (pulls `umap-learn`; typically also standalone `hdbscan`).
- OpenAI client for `bertopic.representation.OpenAI`.
- Existing: `scikit-learn`, `matplotlib`, AWS/`boto3` for one-time embedding cache backfill, dataset loader under `shared/data/`.

## Out of scope (v1)

- Mirror-text BERTopic run (same layout under `outputs/**/mirror/` later)
- Using topic features in a keep/remove classifier (`export_features.py` can come after viz)
- Re-embedding posts with SentenceTransformers or any non-Titan model inside BERTopic

## Run order

UTC run stamps use format `YYYYMMDDTHHMMSSZ` (e.g. `20260805T131500Z`).

```bash
# Install optional BERTopic stack (once per env)
uv sync --extra bertopic

# Stage 1 — Titan cache for original posts (no Bedrock when cache complete)
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py
# First populate / refresh from DynamoDB+S3 identity cache:
# PYTHONPATH=. uv run --extra bertopic python \
#   experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py \
#   --refresh-from-identity-cache
# Optional Bedrock for residuals only:
#   ... --refresh-from-identity-cache --backfill

# Stage 2 — fit BERTopic (no LLM); smoke uses --sample-size 50
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --sample-size 50

# Stage 3 — post-hoc LLM labels (gpt-5.4-nano); skip topic -1
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>

# Stage 4 — three overlays from shared umap_2d.npy
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>

# Smoke (Step 6): --sample-size 50, then stop for approval
# Production (Step 7, after approval): omit --sample-size (all original posts)
```
