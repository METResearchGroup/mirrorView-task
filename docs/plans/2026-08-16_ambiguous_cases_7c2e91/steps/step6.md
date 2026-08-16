# Step 6: Predict ambiguity from text

## Goal

Test whether post text predicts the adjusted ambiguity score above what it predicts for the modal keep or remove label, using Titan embeddings and shared surface features only. Do not call language-model APIs and do not use Stage 1 features that may encode the human label.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e5_text_predictability.py
```

Flow: load post effects and post frame, load Titan original embeddings from `experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/`, compute shared surface features from `shared/textual_features/` for character count, word count, punctuation density, reading ease, Flesch-Kincaid grade, valence, intergroup, and PRIME, train ridge or logistic models for modal remove label and for continuous adjusted ambiguity, report held-out metrics with an 80/20 split on posts with three or more raters, also report label-model accuracy on posts with one or two raters as an extra check, write feature importance tables that contrast the two targets, and score the grey-zone contrast that posts with high PRIME or intergroup flags and low valence positivity are enriched in the top ambiguity quartile.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E5 contract |
| `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/` | Titan vectors |
| `/workspace/shared/textual_features/registry.py` | Surface feature registry |
| `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e2/post_effects.csv` | Ambiguity target |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e5_text_predictability.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e5/metrics.json`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e5/feature_importance.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e5/grey_zone_contrast.csv`

## Files forbidden to change

- `/workspace/experiments/create_llm_features_2026_08_05/**`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**`
- `/workspace/shared/**` except reading `shared/textual_features/`

## Contracts to freeze

### Targets

1. Binary modal remove label: `remove_count > keep_count` on the post frame. Ties are excluded from the classification metrics.
2. Continuous `adjusted_ambiguity_score` from E2. Ties are included.

### Models

Use scikit-learn `LogisticRegression` for the label target and `Ridge` for the ambiguity target. Features are concatenated standardized Titan dimensions plus the named surface features. Split seed is 42. Train only on posts present in both the embedding index and the post frame.

### Metrics JSON keys

`label_test_accuracy`, `label_test_roc_auc`, `ambiguity_test_r2`, `ambiguity_test_pearson_r`, `n_train`, `n_test`, `n_one_or_two_rater_label_check`, `one_or_two_rater_label_accuracy`, `seed`.

### Grey-zone contrast

Among posts with three or more raters, compare the share of posts that are PRIME-positive or intergroup-positive and valence-negative across the top versus bottom quartile of adjusted ambiguity. Write counts and shares to `grey_zone_contrast.csv`.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e5_text_predictability.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
metrics = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e5/metrics.json").read_text())
imp = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e5/feature_importance.csv")
assert "ambiguity_test_pearson_r" in metrics
assert len(imp) > 0
print("e5_ok", round(metrics["ambiguity_test_pearson_r"], 4), round(metrics["label_test_roc_auc"], 4))
PY
```

Expected shape:

```text
e5_ok <r> <auc>
```

## Pass / fail

Pass: metrics file exists, no Stage 1 LLM features used, grey-zone contrast written.

Fail: API calls attempted, Stage 1 features loaded, missing embedding join without an error.

## Commit gate

Commit E5 script and outputs after `e5_ok` prints.
