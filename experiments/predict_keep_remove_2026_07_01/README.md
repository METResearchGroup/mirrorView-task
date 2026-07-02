# Predict keep/remove actions

Our data, `keep_remove_results_2026_06_23.csv`, comes from our latest study run, where we showed users 20 posts and their flips and asked them if they wanted to keep or remove the pair. We did this for 1,200 users and 10,000 total posts.

What we'd like to do is the following:

1. Training a model to see what kind of accuracy we can get.
2. Build baselines and scaling curves for training.
3. Doing feature extraction
4. Training a model on the extracted features to see if they're performant. That way, we have explainable and reproducible features.

We write up the results in `results.md` (which we then compile to `results.pdf`):

`pandoc experiments/predict_keep_remove_2026_07_01/results.md -o experiments/predict_keep_remove_2026_07_01/results.pdf`

We have the following scripts:

- `dataloader.py`: loads in the data from the raw .csv.
- `generate_dataset_metrics.py`: generates the dataset metrics (e.g., number of posts) cited in the writeup.
- `generate_embeddings.py`: generates the embeddings and stores in S3.
