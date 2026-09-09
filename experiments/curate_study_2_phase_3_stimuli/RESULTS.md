# Curate study 2 phase 3 stimuli, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
```

## Available posts with a flip

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 1700 | 2695 | 1698 | 6093 |
| right | 1696 | 3334 | 1354 | 6384 |
| total | 3396 | 6029 | 3052 | 12477 |

The catalog file `experiments/curate_study_2_phase_3_stimuli/flips.csv` has 10,000 rows, and its SHA-256 is `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`. The same bytes are on S3 at `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv`. The catalog has 5,000 left posts and 5,000 right posts, and it has 2,500 low, 5,000 medium, and 2,500 high posts.
