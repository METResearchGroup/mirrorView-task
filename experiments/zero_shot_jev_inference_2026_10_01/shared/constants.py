"""Constants for zero-shot Jev keep or remove inference on Study 2.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import S3_PREFIX"
"""

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPECTED_SPLIT_RECORD_COUNT as EXPECTED_SPLIT,
    EXPECTED_TOTAL_RECORD_COUNT as EXPECTED_ALL,
    EXPECTED_UNANIMOUS_RECORD_COUNT as EXPECTED_UNANIMOUS,
    INPUT_MANIFEST_KEY as SOURCE_INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY as SOURCE_INPUT_RECORDS_KEY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelDefinition
from shared.models.jev.constants import JEV_MODEL_ID

EXPERIMENT_NAME = ZERO_SHOT_VARIANT.experiment_name
S3_BUCKET = ZERO_SHOT_VARIANT.s3_bucket
S3_PREFIX = ZERO_SHOT_VARIANT.s3_prefix
JEV_MODEL = ModelDefinition(
    display_name="Jev 1.13.0",
    folder_name="jev_1_13_0",
    model_id=JEV_MODEL_ID,
)
REMOVE_QUESTION_ID = "is_remove"
STATE_POST_1_KEY = "post_1"
STATE_POST_2_KEY = "post_2"
REMOVE_THRESHOLD = 0.5
INPUT_RECORDS_KEY = ZERO_SHOT_VARIANT.input_records_key
INPUT_MANIFEST_KEY = ZERO_SHOT_VARIANT.input_manifest_key
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_WORKERS = 8
