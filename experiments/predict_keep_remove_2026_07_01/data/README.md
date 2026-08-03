# Data

Dataset loading for the keep/remove experiment.

| File | Purpose |
| --- | --- |
| `dataloader.py` | Trial rows from `keep_remove_results_2026_06_23.csv`; training labels from shared registry `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`. |

The slim trial CSV lives at the experiment root: `keep_remove_results_2026_06_23.csv`.
Training labels are the shared materialized modal keep/remove dataset (8791 rows).

## Usage

```python
from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader

trials = Dataloader().load_trial_dataframe()
training = Dataloader().load_training_dataframe()
```

## Consumers

Used by `embeddings/`, `models/*`, and `reports/generate/`.
