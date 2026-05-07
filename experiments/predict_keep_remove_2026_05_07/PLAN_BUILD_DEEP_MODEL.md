# Plan: Build Deep Model for Keep/Remove Prediction

## Goal

Build a hybrid deep-learning classifier for `keep_remove_label` that combines:

1. Existing analysis-label/tabular features.
2. Text embeddings for `original_text` and `mirror_text`.

Then train/evaluate with reproducible splits and track experiments in Weights & Biases (W&B).

---

## Recommended v1 Strategy

Start with a practical baseline:

1. Precompute OpenAI embeddings for both texts.
2. Concatenate:
   - tabular analysis features
   - `embedding(original_text)`
   - `embedding(mirror_text)`
   - optional interaction vectors (`abs(diff)`, elementwise product)
3. Train an MLP classifier head (binary output).
4. Track all runs in W&B.

This is the fastest path to a strong baseline before full transformer fine-tuning.

---

## 1) Embeddings Pipeline

### What to embed

- Use unique `post_id` rows for embedding generation (avoid recomputing duplicate text pairs).
- For each `post_id`, store:
  - `orig_embedding`
  - `mirror_embedding`

### API/model choice

- Use OpenAI embeddings API (easiest operationally).
- Pick one embedding model and lock it in metadata (e.g. `text-embedding-3-small` or `text-embedding-3-large`).

### Implementation details

- Batch API calls (e.g., 64-256 texts/batch depending on limits).
- Retry with exponential backoff on rate limits/errors.
- Cache embeddings to disk (Parquet/JSONL/NPY) keyed by `post_id`.
- Add version metadata:
  - embedding model name
  - creation timestamp
  - text hash (optional, for cache invalidation)

### Data join

- Join per-`post_id` embeddings back into the row-level training dataframe so each participant decision row has both embeddings.

---

## 2) Train/Test Split and Tensor Shapes

## Important leakage rule

Primary eval should split by `post_id` (group split), not random row split.  
Otherwise the same text pair can land in train and test.

Optional secondary analyses:

- split by `prolific_id` (participant generalization)
- random row split (diagnostic only)

### Tensor representation

Per batch:

- `x_tab`: tabular features, shape `[B, F_tab]`
- `x_orig`: original embedding, shape `[B, D]`
- `x_mirr`: mirror embedding, shape `[B, D]`
- optional:
  - `x_diff = |x_orig - x_mirr|`, shape `[B, D]`
  - `x_prod = x_orig * x_mirr`, shape `[B, D]`

Final:

- `x = concat([x_tab, x_orig, x_mirr, x_diff, x_prod])`
- shape `[B, F_tab + 4D]` (or `[B, F_tab + 2D]` without interactions)
- target `y`: shape `[B]`, values `{0,1}`

### Preprocessing

- Standardize tabular features (`fit` on train only).
- Convert all model inputs to `float32`.
- Fill missing tabular values consistently (e.g. zeros).
- Keep embedding normalization strategy fixed across runs (recommended: L2 normalize).

---

## 3) Model Options

## Option A (recommended first): Embeddings + MLP head

- Input: concatenated vector (tabular + embeddings + optional interactions)
- Architecture example:
  - Linear -> GELU/ReLU -> Dropout
  - Linear -> GELU/ReLU -> Dropout
  - Linear(1)
- Loss: `BCEWithLogitsLoss`
- Output: sigmoid probability for keep.

Pros: simple, fast, robust with current dataset size.

## Option B: HuggingFace cross-encoder fine-tune

- Concatenate text pair at tokenizer level:
  - `original_text [SEP] mirror_text`
- Backbone options:
  - `microsoft/deberta-v3-base`
  - `roberta-base`
- Add classifier head.
- Optional fusion: concatenate pooled transformer representation with projected tabular vector.

Pros: richer task-specific adaptation.  
Cons: heavier compute, higher overfitting risk on smaller data.

### Recommendation

Run Option A first as the reference baseline; then test Option B and compare on the same grouped split.

---

## 4) Training Loop + W&B Tracking

### Reproducibility

Set seed to `42` everywhere:

- Python random
- NumPy
- PyTorch CPU/CUDA
- DataLoader worker init if used

### Training loop outline

1. Build `Dataset` + `DataLoader` for train/val/test.
2. Forward pass -> logits.
3. Compute `BCEWithLogitsLoss`.
4. Backprop + optimizer step.
5. Evaluate each epoch on val/test.
6. Early stopping on validation AUC or F1.
7. Save best checkpoint and artifacts.

### Metrics to log (train and test)

- loss
- accuracy
- precision
- recall
- f1
- roc_auc

### W&B logging

Log:

- config (seed, split method, embedding model, architecture, LR, batch size)
- per-epoch metrics
- final metrics
- artifacts:
  - model checkpoint
  - scaler/preprocessor
  - predictions CSV
  - metadata JSON

---

## Suggested Experiment Ladder

1. Existing logistic/XGBoost baselines (already done).
2. Embeddings-only + logistic regression.
3. Hybrid MLP (tabular + embeddings).
4. HF cross-encoder (text-only).
5. HF cross-encoder + tabular fusion.

Use fixed seed and consistent split strategy for fair comparison.

---

## Concrete Deliverables Checklist

- [ ] `embeddings.py` pipeline with cache + metadata.
- [ ] Dataloader extension to attach embeddings.
- [ ] Grouped split utility (by `post_id` primary).
- [ ] `deep_mlp.py` model strategy with train/test metrics.
- [ ] W&B-integrated training script/CLI options.
- [ ] Timestamped output folder with:
  - [ ] `metadata.json`
  - [ ] `training_report.json`
  - [ ] `model checkpoint`
  - [ ] `test_predictions.csv`
  - [ ] `feature schema/config snapshot`
