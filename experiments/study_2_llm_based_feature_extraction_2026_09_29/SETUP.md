# Setup

## Data

- `STUDY_2_RESULTS_FULL` at `s3://mirrorview-experimental-artifacts/shared/data/raw/study_2/results/full.csv`. Load with `shared.data.dataloader.load_dataset`.
- `STUDY_2_STIMULI` at `s3://mirrorview-experimental-artifacts/shared/data/raw/study_2/stimuli/flips.csv`. Load with `shared.data.dataloader.load_dataset`.

## Outputs

Artifacts upload to `s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

## Commands

### Step 1: cohort and batches

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step1_setup/run.py
```

### Step 2: mine candidate features

OpenAI calls are synchronous chat completions. asyncio runs them, and at most 8 run at once.

Smoke (five batches, writes estimates):

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --smoke
```

Full run (requires `step2_mine_candidate_features/estimates.json` from smoke):

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --full
```

### Step 3: deduplicate and embed features

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/run.py
```

### Step 4: cluster feature embeddings

K-means runs twice on the step 3 vectors, with 15 clusters for kept-post features and 15 clusters for removed-post features.

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
```

### Step 5: name clusters

Each prompt receives the 50 features closest to that cluster's center. Smoke names the first five clusters. The full run names all 30.

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --smoke
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --full
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --write-label-details
```
