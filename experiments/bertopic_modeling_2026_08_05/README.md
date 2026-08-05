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

For our use case, we run BERTopic on the original post embeddings. We've already previously generated the text embeddings, using Amazon Titan, for other experiments we've done in this repo. Later work will replicate this but for the mirrored post embeddings. We fit on all the posts.

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
