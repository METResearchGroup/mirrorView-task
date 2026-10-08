# Step 1: Join the split posts to the feature table

## Proposal sections implemented

- Posts and labels
- Train and test posts
- Features
- File structure
- Schema and key interfaces, modeling frame and split manifest
- Step 1, Join the split posts to the feature table

## Scope

- Caller: `experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part1_load_data.load.main`
- Task: Draw the confirmed holdout, join the 30 binary feature columns, and upload the train frame, the test frame, and the split manifest.
- Out of scope: fitting either regression, scoring, and `RESULTS.md` metric tables.

## Files to inspect

- `/workspace/docs/plans/2026-10-08_train_linear_model_on_llm_features_50850f/proposal.md`
- `/workspace/shared/data/dataloader.py`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/utils/upsample.py`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`
- `/workspace/lib/aws/s3.py`

## Files allowed to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/README.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/SETUP.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/RESULTS.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/.gitignore`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/shared/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/shared/constants.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_load.py`

## Files forbidden to change

- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/utils/upsample.py`
- `/workspace/pyproject.toml`
- `/workspace/experiments/lora_finetuning_study2_2026_10_04/`

## Contract

`shared/constants.py` defines:

- `EXPERIMENT_NAME = "train_linear_model_on_llm_generated_features_2026_10_07"`
- `S3_BUCKET` imported from `experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants.S3_BUCKET`
- `S3_PREFIX = f"experiments/{EXPERIMENT_NAME}/"`
- `RANDOM_SEED = 1`
- `TEST_FRACTION = 0.20`
- `LOGISTIC_THRESHOLD = 0.5`
- `FEATURE_OBJECT_KEY` built from that experiment's `S3_PREFIX` and `POST_FEATURE_LABELS_KEY`
- `FEATURE_COLUMNS = tuple(sorted(LABEL_TO_DETAIL))`
- local output directory `experiments/train_linear_model_on_llm_generated_features_2026_10_07/outputs/`
- relative keys `data/train.parquet`, `data/test.parquet`, and `data/split_manifest.json`

`build_frames(regular, upsampled, features) -> tuple[pd.DataFrame, pd.DataFrame, dict]` does not read S3. `main` loads the two registry tables with `shared.data.dataloader.load_dataset` and downloads the feature parquet with `lib.aws.s3.S3.get_bytes`.

The holdout uses one `numpy.random.default_rng(RANDOM_SEED)`. Sort the unique post ids in label 0, draw `math.floor(TEST_FRACTION * n)` of them, then do the same for label 1. The test frame is the regular rows whose `post_id` is in that draw, in the regular CSV order. The train frame is the upsampled rows whose `post_id` is outside that draw, in the upsampled CSV order. Do not sort either frame before saving or fitting.

Join features with a left merge on `post_id` and `validate="many_to_one"` for train and `validate="one_to_one"` for test. Keep the left row order.

The modeling columns, in order, are `post_id`, `keep_remove_label`, `n_remove`, `n_raters`, `remove_proportion`, then `FEATURE_COLUMNS`. `remove_proportion` is `n_remove / n_raters`. Do not store post text.

The manifest is a JSON object with `seed`, `test_fraction`, `class_order` of `["keep", "remove"]`, `train_dataset`, `test_dataset`, `feature_object_key`, `feature_columns`, `train_row_count`, `test_row_count`, and `test_post_ids`. `test_post_ids` is sorted.

Raise `ValueError` when a row has `n_raters` other than 5, when a feature column is missing, when a joined feature cell is null, when the regular table repeats a `post_id`, or when a train post id is also a test post id.

`main` writes the three files under `outputs/`, uploads them with `S3.upload_bytes` to `S3_PREFIX` plus the relative key, and overwrites an existing object. It prints one line:

```text
train_rows=11663 train_keep=5825 train_remove=5838 train_unique=7953 test_rows=1988 test_keep=1456 test_remove=532 test_unique=1988 overlap=0
```

`README.md` is two lines: the title, then a pointer to `SETUP.md` and `RESULTS.md`. `SETUP.md` names the two registry tables, the feature object key, and the three output keys. `RESULTS.md` says the metric tables are written in step 4. `.gitignore` contains `outputs/`.

## Tests

Write `tests/test_load.py` first. It must fail before `build_frames` exists. Use small in-memory frames. No S3.

The tests must show:

- A balanced tiny table with seed 1 holds out `floor(0.20 * n)` unique ids from each class, keep first.
- Copied remove rows for a test id stay out of train, and copied remove rows for a train id stay in train, in source order.
- A missing feature column, a null feature cell, a rater count other than 5, a repeated regular post id, and a train and test overlap each raise `ValueError`.
- The saved column order is the modeling order above, and `remove_proportion` equals `n_remove / n_raters`.

## Implementation order

1. Add the package markers, `.gitignore`, `README.md`, `SETUP.md`, the `RESULTS.md` placeholder, and `shared/constants.py`. Commit.
2. Add the failing tests. Commit.
3. Implement `build_frames` and `main`. Commit.

Suggested commit messages are `feat: add the LLM-feature regression package`, `test: cover the split-label feature join`, and `feat: build the split-label regression frames`.

## Verification

Run from `/workspace`:

```bash
PYTHONPATH=. uv run pytest experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_load.py -q
```

Expected: all tests passed, exit code 0.

Then run the live load:

```bash
PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part1_load_data.load
```

Expected stdout is exactly:

```text
train_rows=11663 train_keep=5825 train_remove=5838 train_unique=7953 test_rows=1988 test_keep=1456 test_remove=532 test_unique=1988 overlap=0
```

Fail the step if that line differs, if `outputs/` is tracked by git, or if any forbidden file changed.
