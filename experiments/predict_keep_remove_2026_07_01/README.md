# Predict keep/remove actions

Predict whether users keep or remove an original/mirror post pair, using `keep_remove_results_2026_06_23.csv`.

## Layout

| Path | What |
| --- | --- |
| [`data/`](data/) | Dataset loading |
| [`embeddings/`](embeddings/) | Embedding generation + feature vectors |
| [`models/`](models/) | Trainers (logistic, XGBoost, ModernBERT, LLM API, fine-tuning) |
| [`reports/`](reports/) | Figure generators for the writeup |
| [`results.md`](results.md) | Writeup (compile to PDF below) |
| [`PROPOSAL.md`](PROPOSAL.md) | Experiment goals / ladder |
| [`HOW_TO_TRAIN_LANGUAGE_MODELS.md`](HOW_TO_TRAIN_LANGUAGE_MODELS.md) | Language-model training notes |
| [`HOW_TO_DO_LLM_FINETUNING.md`](HOW_TO_DO_LLM_FINETUNING.md) | Fine-tuning notes |
| [`HOW_TO_DO_EXPLAINABILITY.md`](HOW_TO_DO_EXPLAINABILITY.md) | Explainability notes |
| [`HOW_TO_DO_CLUSTERING.md`](HOW_TO_DO_CLUSTERING.md) | Clustering notes |

```bash
pandoc experiments/predict_keep_remove_2026_07_01/results.md \
  -o experiments/predict_keep_remove_2026_07_01/results.pdf
```
