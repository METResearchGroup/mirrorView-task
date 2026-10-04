"""Fixed S3 paths, counts, and model registry for Study 2 zero-shot inference."""

from __future__ import annotations

from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelDefinition

EXPERIMENT_S3_BUCKET = ZERO_SHOT_VARIANT.s3_bucket
EXPERIMENT_S3_ROOT = ZERO_SHOT_VARIANT.s3_root
INPUT_RECORDS_KEY = ZERO_SHOT_VARIANT.input_records_s3_key
INPUT_MANIFEST_KEY = ZERO_SHOT_VARIANT.input_manifest_s3_key

EXPECTED_TOTAL_RECORD_COUNT = 13992
EXPECTED_UNANIMOUS_RECORD_COUNT = 4051
EXPECTED_SPLIT_RECORD_COUNT = 9941
FIVE_RATER_COUNT = 5
UNANIMOUS_REMOVE_VOTES = frozenset({0, FIVE_RATER_COUNT})

INPUT_MANIFEST_SCHEMA_VERSION = "study2-five-labeler-input-v1"
REMOVE_LABEL_VALUE = 1
PROBABILITY_THRESHOLD = 0.5

def get_model_definition_by_folder(folder_name: str) -> ModelDefinition:
    """Return the registry entry for ``folder_name``.

    Raises
    ------
    ValueError
        When ``folder_name`` is not one of the confirmed registry folders.
    """
    for entry in MODEL_REGISTRY:
        if entry.folder_name == folder_name:
            return entry
    raise ValueError(f"unknown model folder: {folder_name}")


MODEL_REGISTRY: tuple[ModelDefinition, ...] = (
    ModelDefinition(
        display_name="Amazon Nova Micro",
        folder_name="amazon_nova_micro",
        model_id="us.amazon.nova-micro-v1:0",
    ),
    ModelDefinition(
        display_name="Qwen 3 32B",
        folder_name="qwen3_32b",
        model_id="qwen.qwen3-32b-v1:0",
    ),
    ModelDefinition(
        display_name="OpenAI GPT-5.6 Terra",
        folder_name="openai_gpt_5_6_terra",
        model_id="us.openai.gpt-5.6-terra",
    ),
    ModelDefinition(
        display_name="Claude Sonnet 5.5",
        folder_name="claude_sonnet_5_5",
        model_id="us.anthropic.claude-sonnet-5-5",
    ),
)
