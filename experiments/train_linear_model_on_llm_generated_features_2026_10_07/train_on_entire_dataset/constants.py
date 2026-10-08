"""Settings for the full split-label regression run."""

from pathlib import Path

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    POST_FEATURE_LABELS_KEY,
    S3_BUCKET,
    S3_PREFIX as FEATURE_S3_PREFIX,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.label_to_detail import (
    LABEL_TO_DETAIL,
)
from lib.constants import REPO_ROOT

EXPERIMENT_NAME = "train_linear_model_on_llm_generated_features_2026_10_07"
RUN_NAME = "train_on_entire_dataset"
PACKAGE_DIR = (
    REPO_ROOT / "experiments" / EXPERIMENT_NAME / RUN_NAME
)
OUTPUT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_NAME / "outputs" / RUN_NAME
S3_PREFIX = f"experiments/{EXPERIMENT_NAME}/{RUN_NAME}/"
FEATURE_OBJECT_KEY = f"{FEATURE_S3_PREFIX}{POST_FEATURE_LABELS_KEY}"
FEATURE_COLUMNS = tuple(sorted(LABEL_TO_DETAIL))
LOGISTIC_THRESHOLD = 0.5
LOGISTIC_RANDOM_STATE = 1
LOGISTIC_MAX_ITER = 1000
REQUIRED_LABELERS = 5
ID_COLUMN = "post_id"
LABEL_COLUMN = "keep_remove_label"
REMOVE_COUNT_COLUMN = "n_remove"
RATER_COUNT_COLUMN = "n_raters"
PROPORTION_COLUMN = "remove_proportion"
MODELING_PREFIX = (
    ID_COLUMN,
    LABEL_COLUMN,
    REMOVE_COUNT_COLUMN,
    RATER_COUNT_COLUMN,
    PROPORTION_COLUMN,
)
