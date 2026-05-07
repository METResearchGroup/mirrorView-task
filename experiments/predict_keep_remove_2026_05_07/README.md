# Predicting which pairs of posts to keep/remove

The goal here is to create a model to overfit on our initial pilot data. We want to see what it would look like (in terms of problem setup, loss, etc.) to train a model to predict the keep/remove decisions. By creating a v1 that's overfit on our initial pilot data, we can make informed decisions about how much data we need, how to design the problem, etc.

The output in question is the binary keep/remove decision, for each pair of posts.

Some ideas for features:

- Embeddings: original text embeddings, mirrored text embeddings.
- Text features: We can repurpose labels from `experiments/mirrors_content_analysis_2026_04_24/`.
- User features: political party, condition, gender, age

Models:

- Simple: logistic regression, XGBoost. Would be limited to using the non-embedding features, but that's OK.
- Complex: transformer-based NN models + classification head.
