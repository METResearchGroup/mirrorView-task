# Simplified keep/remove embedding + training pipeline

**Origin:** Exported from Cursor plan **`simplified_model_training_fc01b3a2`** (`simplified_model_training_fc01b3a2.plan.md`).

**Asset folder (this repo):** `docs/plans/2026-05-13_simplified_keep_remove_training_582914/`

This work scope has **no UI changes** to the product; screenshots are **not applicable**.

---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

---

## Overview

Build a reproducible training workflow for majority linked-fate keep/remove prediction in `experiments/simplified_predict_remove_2026_05_13`. Load one row per `post_id` from `dataloader.py`, emit one Titan embedding each for `original_text` and `mirror_text`, store verified JSON on S3 with DynamoDB pointers, then train per-model bundles under `models/{model}/` with UTC timestamped artifacts, metrics, metadata, and run writeups. First models: logistic regression and XGBoost, with interfaces frozen so MLP heads or fine-tuned cross-encoders can plug in later without changing the embedding join contract.

---

## Happy Flow

1. `experiments/simplified_predict_remove_2026_05_13/dataloader.py` aggregates parent pilot rows into one row per `post_id` with `sampled_stance`, `sampled_toxicity`, texts, aggregated `decision`, and binary `keep_remove_label` (\(1\)=remove, \(0\)=keep).
2. `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` emits two embedding tasks per row (original mirror roles), uploads Bedrock payloads to S3, writes DynamoDB pointer rows keyed by deterministic `embedding_id`, then re-reads DynamoDB → S3 and verifies vectors (`tqdm` loops + Rich success/failure).
3. Training scripts (`models/logistic_regression/train.py`, `models/xgboost/train.py`) load rows, resolve vectors via DynamoDB/S3 identities, stratified split **before** join to avoid preprocessing leakage, build dense interaction features + one-hot metadata in `features.py`, fit the model, and write timestamped dirs under each `models/<name>/outputs/`.

---

## Data Flow

Pilot CSVs → parent `predict_keep_remove_2026_05_07` dataloader joins → simplified dataloader aggregates by `post_id` → Bedrock Titan embeds each distinct text chunk → hashed `embedding_id` → S3 JSON + DynamoDB `{embedding_id → s3_key, …, post_id, text_role}` → training re-fetches S3 payloads by identity hash → concatenated numeric design matrix (+ stance/toxicity OHE fitted on train) → logits / trees → artifacts + `metrics.json`.

---

## Interface or Contract Freeze

- Timestamped runs: `lib.timestamp_utils.get_current_timestamp()`, paths `experiments/simplified_predict_remove_2026_05_13/models/{model}/outputs/{YYYY_MM_DD-HH:MM:SS}/`.
- Target: `keep_remove_label == 1` ⇒ remove.
- Unique `post_id`; fail on duplicates or blank texts (with explicit `post_id` / `text_role`).
- Dynamo pointer minimally: `embedding_id`, `s3_bucket`, `s3_key`, `text_sha256`, `created_at`, `model_id`, `dimensions`, `normalize`, `post_id`, `text_role`.
- S3 JSON retains `create_embedding()` shape (`text`, `model_id`, `dimensions`, `normalize`, `embedding`, `input_text_token_count`).
- Per run: `metadata.json`, `metrics.json`, `test_predictions.csv`, `model.pkl`, `preprocessor.pkl`, plus coefficient or importance CSVs.

---

## Serial Coordination Spine

1. Land and smoke-test embedding pipeline (`generate_embeddings.py --limit 2`).
2. Full embedding sweep for all simplified rows.
3. Shared `features.py` / `splits.py` stabilized on embedding contract.
4. Logistic regression folder + run + `RESULTS.md`.
5. XGBoost folder + run + `RESULTS.md`, compare gaps train vs test to spot overfitting.

---

## Parallel Task Packets

### Task A: Embedding Generation Pipeline
Task ID: `embedding-generator`

**Objective:** Create `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` that generates, uploads, re-loads, verifies, and reports embeddings for all simplified examples.

**Why parallelizable:** This task owns only embedding generation and does not touch model folders.

**Exact files to inspect:**
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`
- `experiments/simplified_predict_remove_2026_05_13/experiment_bedrock_embeddings.py`
- `experiments/simplified_predict_remove_2026_05_13/experiment_create_embedding_and_upload.py`
- `lib/aws/dynamodb.py`
- `lib/aws/s3.py`
- `lib/aws/embedding_identity.py`

**Exact files allowed to change:**
- `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`
- `experiments/simplified_predict_remove_2026_05_13/README.md` only if documenting the command is necessary

**Exact files forbidden to change:**
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`
- `experiments/simplified_predict_remove_2026_05_13/experiment_bedrock_embeddings.py`
- `experiments/simplified_predict_remove_2026_05_13/experiment_create_embedding_and_upload.py`
- `lib/aws/dynamodb.py`
- `lib/aws/s3.py`
- `lib/aws/embedding_identity.py`

**Preconditions:**
- AWS credentials can invoke Bedrock, put/get S3 objects, and put/get DynamoDB rows.
- Use existing constants from `experiment_create_embedding_and_upload.py`: `S3_BUCKET`, `DYNAMODB_TABLE_NAME`, `S3_PREFIX`, and `AWS_REGION`, unless CLI options override them.

**Dependency tasks:** none.

**Required contracts and invariants:**
- `generate_embeddings(df: pd.DataFrame | None = None, ...) -> EmbeddingGenerationResult` must be callable from Python and from a CLI `main()`.
- Use `tqdm` for both generation and verification loops.
- If all vectors verify, print `SUCCESS` in green with a checkmark using `rich`.
- If any vector fails, print `FAILED` in red with an X and raise a non-zero exception.
- Do not silently skip blank text; fail with a clear error listing `post_id` and `text_role`.

**Step-by-step implementation instructions:**
1. Define constants `TEXT_ROLE_ORIGINAL = "original_text"` and `TEXT_ROLE_MIRROR = "mirror_text"`.
2. Add a dataclass `EmbeddingGenerationResult` with counts, bucket/table names, model metadata, generated rows, and failed verification rows.
3. Add `build_text_instances(df)` to return exactly two rows per input row and validate required columns.
4. Add `generate_embeddings(...)` that creates S3, DynamoDB, optionally ensures the table exists, loops over instances with `tqdm`, calls `create_embedding()`, writes S3 JSON, and writes DynamoDB metadata.
5. Reuse or move locally the `_vectors_equivalent()` logic from `experiment_create_embedding_and_upload.py`.
6. Add `verify_embeddings(...)` that loops over generated rows with `tqdm`, gets the DynamoDB item, fetches S3 JSON, and compares loaded vs generated vector.
7. Add a CLI entry point with options for `--bucket`, `--table`, `--s3-prefix`, `--limit`, `--skip-table-create`, `--normalize/--no-normalize`.
8. Print a concise summary: text instances generated, embeddings uploaded, verified count, model id, dimensions, S3 prefix.

**Exact verification commands:**
- `PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py --limit 2`
- `PYTHONPATH=. uv run python -m py_compile experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`

**Expected outputs from verification:**
- The first command shows two `tqdm` progress bars, then green `SUCCESS` with a checkmark.
- The second command exits with code `0` and no output.

**Done-when checklist:**
- `generate_embeddings.py` exists and exposes `generate_embeddings()`.
- Both progress bars exist.
- DynamoDB and S3 round-trip verification uses every generated embedding row.
- Failures include `post_id`, `text_role`, `embedding_id`, and reason.

**Coordinator review checklist:**
- Confirm no hardcoded local file writes except optional metadata/cache outputs if explicitly requested.
- Confirm the function accepts a dataframe from `Dataloader().load_training_dataframe()`.
- Confirm the S3 key is deterministic, e.g. `f"{s3_prefix}{embedding_id}.json"`.

### Task B: Shared Feature and Split Utilities
Task ID: `feature-builder`

**Objective:** Create shared utilities to join verified embeddings to the simplified dataframe and produce train/test matrices for multiple models.

**Why parallelizable:** This task can be written against the frozen embedding schema without touching individual model training loops.

**Exact files to inspect:**
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`
- `experiments/predict_keep_remove_2026_05_07/models/logistic_regression.py`
- `experiments/predict_keep_remove_2026_05_07/models/xgboost.py`

**Exact files allowed to change:**
- `experiments/simplified_predict_remove_2026_05_13/features.py`
- `experiments/simplified_predict_remove_2026_05_13/splits.py` if split code is separated

**Exact files forbidden to change:**
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`
- All files under `experiments/predict_keep_remove_2026_05_07/`

**Preconditions:**
- Task A's embedding row contract is frozen.

**Dependency tasks:** `embedding-generator` for final integration, but utilities can be unit-tested with synthetic data.

**Required contracts and invariants:**
- One-hot encode only `sampled_stance` and `sampled_toxicity`.
- Fit encoders/scalers on train only, then transform test.
- Include embedding interaction features: original, mirror, absolute difference, elementwise product, cosine similarity.
- Return feature names for coefficients/importances.

**Step-by-step implementation instructions:**
1. Add a function to construct an embedding lookup keyed by `(post_id, text_role)` or by deterministic `embedding_id`.
2. Add `join_embeddings(df, embedding_rows)` that creates `embedding_original_text` and `embedding_mirror_text` columns.
3. Add `make_train_test_split(df, train_split=0.8, seed=42)` using stratification on `keep_remove_label`.
4. Add a sklearn-compatible preprocessing path, preferably `ColumnTransformer`/`OneHotEncoder` for categorical metadata plus dense numeric vectors expanded into columns.
5. Add helper functions for metrics: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix.

**Exact verification commands:**
- `PYTHONPATH=. uv run python -m py_compile experiments/simplified_predict_remove_2026_05_13/features.py`
- If `splits.py` exists: `PYTHONPATH=. uv run python -m py_compile experiments/simplified_predict_remove_2026_05_13/splits.py`

**Expected outputs from verification:**
- Commands exit with code `0` and no output.

**Done-when checklist:**
- Feature builder can produce `X_train`, `X_test`, `y_train`, `y_test`, and `feature_names`.
- Categorical one-hot dimensions are stable between train and test.
- Missing embeddings raise a clear error.

**Coordinator review checklist:**
- Confirm no test-set leakage in one-hot/scaler fitting.
- Confirm `keep_remove_label` is never included as a feature.
- Confirm feature names align with matrix columns.

### Task C: Logistic Regression Model Folder
Task ID: `logistic-regression-model`

**Objective:** Add `models/logistic_regression/model.py`, `train.py`, `outputs/`, and `RESULTS.md`, then run it and record results.

**Why parallelizable:** Owns only the logistic regression folder and consumes shared utilities.

**Exact files to inspect:**
- `experiments/predict_keep_remove_2026_05_07/models/logistic_regression.py`
- `experiments/predict_keep_remove_2026_05_07/train.py`
- `experiments/simplified_predict_remove_2026_05_13/features.py`
- `lib/timestamp_utils.py`

**Exact files allowed to change:**
- `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py`
- `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py`
- `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/RESULTS.md`
- `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/outputs/` generated run folders

**Exact files forbidden to change:**
- `experiments/simplified_predict_remove_2026_05_13/models/xgboost/**`
- `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`

**Preconditions:**
- Task B is merged.
- Embeddings have been generated and are readable.

**Dependency tasks:** `feature-builder`, `embedding-generator`.

**Required contracts and invariants:**
- Use `LogisticRegression(max_iter=2000, solver="liblinear", class_weight="balanced" optional via CLI)` or similar conservative sklearn setup.
- Save model/preprocessor using pickle/joblib.
- `metadata.json` must include timestamp, seed, train/test rows, embedding model id, embedding dimensions, feature set description, and command/config.
- `RESULTS.md` must summarize latest run path, metrics, and brief interpretation.

**Step-by-step implementation instructions:**
1. Create the folder structure.
2. In `model.py`, define `LogisticRegressionKeepRemoveModel` with `fit`, `predict`, `predict_proba`, and artifact save support.
3. In `train.py`, load dataframe, load or retrieve embeddings, build features, train, evaluate, and save artifacts under `outputs/{timestamp}`.
4. Save `metrics.json`, `metadata.json`, `test_predictions.csv`, `feature_coefficients.csv`, and serialized model/preprocessor.
5. Print output directory and core metrics.
6. After running, update `RESULTS.md` with actual metrics.

**Exact verification commands:**
- `PYTHONPATH=. uv run python -m py_compile experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py`
- `PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py --seed 42 --train-split 0.8`

**Expected outputs from verification:**
- Compile command exits with code `0`.
- Train command prints an output directory like `.../models/logistic_regression/outputs/2026_05_13-10:30:00` and metrics including ROC-AUC and F1.

**Done-when checklist:**
- Logistic regression run creates a timestamped output folder.
- `RESULTS.md` names the latest timestamped run and includes test metrics.
- Coefficients are saved with feature names.

**Coordinator review checklist:**
- Confirm probabilities in `test_predictions.csv` are remove probabilities.
- Confirm metadata references the exact embedding source/config.

### Task D: XGBoost Model Folder
Task ID: `xgboost-model`

**Objective:** Add `models/xgboost/model.py`, `train.py`, `outputs/`, and `RESULTS.md`, then run it and record results.

**Why parallelizable:** Owns only the XGBoost folder and consumes shared utilities.

**Exact files to inspect:**
- `experiments/predict_keep_remove_2026_05_07/models/xgboost.py`
- `experiments/simplified_predict_remove_2026_05_13/features.py`
- `lib/timestamp_utils.py`

**Exact files allowed to change:**
- `experiments/simplified_predict_remove_2026_05_13/models/xgboost/model.py`
- `experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py`
- `experiments/simplified_predict_remove_2026_05_13/models/xgboost/RESULTS.md`
- `experiments/simplified_predict_remove_2026_05_13/models/xgboost/outputs/` generated run folders

**Exact files forbidden to change:**
- `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/**`
- `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`
- `experiments/simplified_predict_remove_2026_05_13/dataloader.py`

**Preconditions:**
- Task B is merged.
- Embeddings have been generated and are readable.

**Dependency tasks:** `feature-builder`, `embedding-generator`.

**Required contracts and invariants:**
- Use `XGBClassifier` with binary objective and fixed seed.
- Include class imbalance handling with `scale_pos_weight = n_negative / n_positive` unless a CLI flag disables it.
- Save feature importances with feature names.
- `RESULTS.md` must summarize latest run path, metrics, and brief interpretation.

**Step-by-step implementation instructions:**
1. Create the folder structure.
2. In `model.py`, define `XGBoostKeepRemoveModel` with `fit`, `predict`, `predict_proba`, and artifact save support.
3. In `train.py`, load dataframe, load or retrieve embeddings, build features, train, evaluate, and save artifacts under `outputs/{timestamp}`.
4. Save `metrics.json`, `metadata.json`, `test_predictions.csv`, `feature_importances.csv`, and serialized model/preprocessor.
5. Print output directory and core metrics.
6. After running, update `RESULTS.md` with actual metrics.

**Exact verification commands:**
- `PYTHONPATH=. uv run python -m py_compile experiments/simplified_predict_remove_2026_05_13/models/xgboost/model.py experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py`
- `PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py --seed 42 --train-split 0.8`

**Expected outputs from verification:**
- Compile command exits with code `0`.
- Train command prints an output directory like `.../models/xgboost/outputs/2026_05_13-10:30:00` and metrics including ROC-AUC and F1.

**Done-when checklist:**
- XGBoost run creates a timestamped output folder.
- `RESULTS.md` names the latest timestamped run and includes test metrics.
- Feature importances are saved with feature names.

**Coordinator review checklist:**
- Confirm XGBoost does not use labels or text columns directly as features.
- Confirm `scale_pos_weight` is present in metadata.

---

## Integration Order

1. Embedding smoke `--limit 2`.
2. Full `generate_embeddings.py`.
3. Feature utilities compile + smoke against real payloads.
4. Logistic regression train + RESULTS refresh.
5. XGBoost train + RESULTS refresh.
6. Compare models in writeups.

---

## Model Run Order

1. (Optional time-box) Metadata-only logistic ablation—not required for baseline closure.
2. **Required:** Logistic regression full feature matrix (embeddings + interactions + OHE stance/toxicity).
3. **Required:** XGBoost full features.
4. Deferred: shallow MLP on same \(X\); cross-encoder fine-tuning.

---

## Manual Verification

**Note:** `scikit-learn`, `pandas`, `boto3`, `joblib`, `xgboost` for experiments are pinned under `pyproject.toml` **dependency-groups `dev`**; use `PYTHONPATH=. uv run --group dev python …` (or `--all-groups`) when default resolution omits dev tools.

- [x] Embedding smoke test:  
  `PYTHONPATH=. uv run --group dev python experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py --limit 2`  
  Expected: two `tqdm` bars, Rich `SUCCESS`.
- [x] Full embeddings:  
  `PYTHONPATH=. uv run --group dev python experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py`  
  Expected: all \(2 \times n_{\text{posts}}\) vectors uploaded & verified (\(959\) rows → \(1918\) instances succeeded in the implementation batch).
- [x] Compile:  
  `PYTHONPATH=. uv run --group dev python -m py_compile experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py experiments/simplified_predict_remove_2026_05_13/features.py experiments/simplified_predict_remove_2026_05_13/splits.py experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py experiments/simplified_predict_remove_2026_05_13/models/xgboost/model.py experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py`  
  Expected: exit \(0\), silent output.
- [x] Train logistic regression:  
  `PYTHONPATH=. uv run --group dev python experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py --seed 42 --train-split 0.8`
- [x] Train XGBoost:  
  `PYTHONPATH=. uv run --group dev python experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py --seed 42 --train-split 0.8`
- [ ] Each model’s `RESULTS.md` names the latest timestamped directory and lists test accuracy, precision, recall, F1, ROC-AUC, PR-AUC (optional follow-up if not yet committed).
- [ ] Editor / Ruff / Pyright pass on touched files (project-specific).

---

## Final Verification

- [x] `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/` contains `model.py`, `train.py`, `outputs/`.
- [x] `experiments/simplified_predict_remove_2026_05_13/models/xgboost/` contains `model.py`, `train.py`, `outputs/`.
- [x] Latest runs include `metadata.json`, `metrics.json`, `test_predictions.csv` with `post_id`, `keep_remove_label`, `predicted_label`, `predicted_remove_probability`, `model.pkl`, `preprocessor.pkl`, and feature CSVs.
- [ ] Both `RESULTS.md` files present and non-placeholder (if required for repo policy).

---

## Alternative Approaches

- Transformer fine-tune first: slower, less interpretable than frozen Titan + linear/tree baselines on a shared feature matrix.
- Single top-level `train.py`: rejected in favor of per-model `train.py` per contract.
- Local Parquet cache for embeddings: possible speed win; S3 + Dynamo remains source of truth; cache would be derived with provenance in metadata.

---

## Implementation outcome (what was actually done)

This section records what landed in the repository after the plan was executed (including your successful model runs), not a restatement of intent alone.

### Delivered modules and layout

| Area | Path | Role |
|------|------|------|
| Embedding batch + verify | `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` | `generate_embeddings()` / `verify_embeddings()`, Rich `SUCCESS` / `FAILED`, argparse CLI (`--bucket`, `--table`, `--s3-prefix`, `--limit`, `--skip-table-create`, `--normalize` / `--no-normalize`), `tqdm` on generate + verify. |
| Features + metrics | `experiments/simplified_predict_remove_2026_05_13/features.py` | Dynamo/S3 fetch by `embedding_identity_sha256`, `join_embeddings`, `EmbeddingMetadataMatrixBuilder` (dense stack of orig / mirror / abs-diff / Hadamard / cosine + `ColumnTransformer` + `OneHotEncoder` on train only), `classification_metrics_summary` (incl. PR-AUC, confusion tallies). |
| Splits | `experiments/simplified_predict_remove_2026_05_13/splits.py` | Stratified `train_test_split` on `keep_remove_label`. |
| Logistic model | `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py` | `LogisticRegressionKeepRemoveModel` (liblinear, `max_iter=2000`, optional `class_weight`). |
| Logistic train | `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/train.py` | Typer CLI: `--seed`, `--train-split`, `--balanced/--no-balanced`, embedding + AWS overrides. |
| XGBoost model | `experiments/simplified_predict_remove_2026_05_13/models/xgboost/model.py` | `XGBoostKeepRemoveModel` with optional `scale_pos_weight`. |
| XGBoost train | `experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py` | Typer CLI including `--scale-pos-weight/--no-scale-pos-weight`. |
| Output placeholders | `models/*/outputs/.gitkeep` | Ensures `outputs/` exists in git before first run. |

Constants for bucket/table/region continue to be imported from `experiment_create_embedding_and_upload.py` (no changes to that file per plan).

### Embedding generation at scale

- Full pass over the simplified frame (\(959\) posts) produced **\(1918\)** text instances (original + mirror); all were **uploaded and verified** against DynamoDB → S3 round-trip (strict / `math.isclose` helper matching the smoke script).

### Latest training runs (your runs, on disk)

Artifacts use UTC timestamps from `get_current_timestamp()`.

**Logistic regression —** `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/outputs/2026_05_13-16:11:39/`

- Train / test rows: **767 / 192** (`train_split=0.8`, `seed=42`).
- **Test metrics:** accuracy **0.849**, precision **0.620**, recall **0.756**, F1 **0.681**, ROC-AUC **0.879**, PR-AUC **0.730**.
- **Train vs test:** moderate generalization gap (e.g. train ROC-AUC **0.966** vs test **0.879**), consistent with high-dimensional linear model on limited test slice.
- `class_weight`: **balanced** (default).

**XGBoost —** `experiments/simplified_predict_remove_2026_05_13/models/xgboost/outputs/2026_05_13-16:11:44/`

- Same split sizes and seed.
- **Test metrics:** accuracy **0.859**, precision **0.750**, recall **0.512**, F1 **0.609**, ROC-AUC **0.860**, PR-AUC **0.717**.
- **Train metrics are perfect** (accuracy / ROC-AUC **1.0** on train), while test metrics are slightly better on accuracy / ROC-AUC than logistic but **lower recall** on remove—strong signal of **overfitting** to the training fold; worth calling out in model writeups and any production guardrails.
- `scale_pos_weight` ≈ **3.735** from train-class counts (**605** negative, **162** positive remove labels), recorded in `metadata.json`.

Prediction CSV column for the positive (remove) class: **`predicted_remove_probability`** (probability of label `1`).

### Deviations / optional backlog

1. **`RESULTS.md` per model** — Plan called for prose writeups beside each model; as of archiving, **`RESULTS.md` files were not present** under `models/logistic_regression/` or `models/xgboost/`. Recommendation: add them pointing at **`2026_05_13-16:11:39`** and **`2026_05_13-16:11:44`** and summarizing train/test deltas (especially XGBoost train saturation).
2. **Metadata-only logistic ablation** — Explicitly optional in the plan; **not executed** in the recorded runs.
3. **Manual verification CLI** — Plan text used `PYTHONPATH=. uv run python …`; reproducible installs should prefer **`uv run --group dev`** as above unless dev deps are promoted to `[project.dependencies]`.

### Interpretation snippet (for future `RESULTS.md`)

- **Logistic regression** behaves as an interpretable, regularized-ish linear baseline with visible but reasonable train/test ROC gap.
- **XGBoost** achieves near-memorization on train; use test metrics only for comparison, consider stronger regularization, early stopping on a validation fold, or depth / `subsample` sweeps before trusting deployment decisions.
