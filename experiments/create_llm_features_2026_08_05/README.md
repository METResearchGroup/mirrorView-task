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

- llm_generate_features.py
- generate_embeddings.py
- cluster_embeddings.py
- generate_labels_for_embeddings.py

We store our results in outputs/, as

- generated_features/
- generated_embeddings/
- clusters/
- generated_labels/

We use `gpt5.4-nano` for our LLM. We use Amazon Titan for the embeddings (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized).
