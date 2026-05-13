# Predict removes

In this version of predicting removes, we create one label for each post example as to whether it should be kept or removed. This is the aggregate version across all posts, the most common keep/remove choice made.

`experiment_bedrock_embeddings.py` is a small Bedrock smoke test: it embeds two similar strings with Amazon Titan Text Embeddings V2 and prints cosine similarity plus per-call latency. `experiment_create_embedding_and_upload.py` runs a single embedding through the same Titan path, writes the result as JSON to S3 and a pointer row to DynamoDB (`jspsych-mirror-view-embedding-cache`), then reloads the object via that row and checks the vector still matches the fresh Bedrock response (strict equality, with a tiny float fallback after JSON round-trip).
