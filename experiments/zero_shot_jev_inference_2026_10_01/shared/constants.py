"""Constants for zero-shot Jev keep or remove inference on Study 2."""

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPECTED_SPLIT_RECORD_COUNT as EXPECTED_SPLIT,
    EXPECTED_TOTAL_RECORD_COUNT as EXPECTED_ALL,
    EXPECTED_UNANIMOUS_RECORD_COUNT as EXPECTED_UNANIMOUS,
    INPUT_MANIFEST_KEY as SOURCE_INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY as SOURCE_INPUT_RECORDS_KEY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelDefinition
from shared.models.jev.constants import JEV_MODEL_ID

EXPERIMENT_NAME = "zero_shot_jev_inference_2026_10_01"
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = f"experiments/{EXPERIMENT_NAME}/"
JEV_MODEL = ModelDefinition(
    display_name="Jev 1.13.0",
    folder_name="jev_1_13_0",
    model_id=JEV_MODEL_ID,
)
REMOVE_QUESTION_ID = "is_remove"
STATE_POST_1_KEY = "post_1"
STATE_POST_2_KEY = "post_2"
REMOVE_THRESHOLD = 0.5
INPUT_RECORDS_KEY = (
    "experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl"
)
INPUT_MANIFEST_KEY = (
    "experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json"
)
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_WORKERS = 8
