"""Shared constants for the Study 2 LLM feature extraction experiment."""

from pathlib import Path

from lib.constants import REPO_ROOT

EXPERIMENT_NAME = "study_2_llm_based_feature_extraction_2026_09_29"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_NAME
LOCAL_OUTPUT_DIR = EXPERIMENT_DIR / "outputs"
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = f"experiments/{EXPERIMENT_NAME}/"
SEED = 1
REQUIRED_LABELERS = 5
MODAL_REMOVE_MIN_VOTES = 3
MODAL_LABEL_KEEP = "keep"
MODAL_LABEL_REMOVE = "remove"
KEEP_PAIRS_PER_BATCH = 10
REMOVE_PAIRS_PER_BATCH = 10
BATCH_ID_PREFIX = "batch_"
BATCH_ID_WIDTH = 3
COHORT_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "sampled_stance",
    "sample_toxicity_type",
    "n_remove",
    "modal_label",
)
EXPECTED_FIVE_LABEL_PAIRS = 15113
EXPECTED_MODAL_KEEP = 11910
EXPECTED_MODAL_REMOVE = 3203
EXPECTED_BATCHES = 320
EXPECTED_STIMULUS_PAIRS = 20000
SMOKE_QUERY_COUNT = 5
ESTIMATE_BAND = 0.20
COHORT_KEY = "step1_setup/cohort.parquet"
BATCHES_KEY = "step1_setup/batches.jsonl"
