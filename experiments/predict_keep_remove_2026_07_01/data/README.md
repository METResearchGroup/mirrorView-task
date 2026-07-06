# Data

Dataset loading for the keep/remove experiment.

| File | Purpose |
| --- | --- |
| `dataloader.py` | Load `keep_remove_results_2026_06_23.csv` as trial rows or per-post training labels. |

The CSV lives at the experiment root: `keep_remove_results_2026_06_23.csv`.

## Usage

```python
from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader

trials = Dataloader().load_trial_dataframe()
training = Dataloader().load_training_dataframe()
```

## Consumers

Used by `embeddings/`, `models/*`, and `reports/generate/`.
