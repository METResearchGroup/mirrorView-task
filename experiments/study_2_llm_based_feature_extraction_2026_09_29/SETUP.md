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
