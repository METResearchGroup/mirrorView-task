"""Pinned constants for the Phase 2 Part 3 LLM feature experiment.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
    print(constants.SPLIT_SEED)
    "
"""

from __future__ import annotations

from typing import Final

LLM_MODEL_ID: Final = "gpt-6-luna"
LLM_LITELLM_MODEL_ID: Final = "openai/gpt-6-luna"
LLM_REASONING_EFFORT: Final = "none"
SPLIT_SEED: Final = 42
CLUSTER_SEEDS: Final = (42, 43, 44)
DEFAULT_SEED: Final = 42
TEXT_ARMS: Final = ("original_only", "mirror_only", "paired")
BATCH_DESIGN_MIXED: Final = "mixed"
BATCH_DESIGN_SINGLE_CLASS: Final = "single_class"
MAX_KEEP_FEATURES_PER_BATCH: Final = 8
MAX_REMOVE_FEATURES_PER_BATCH: Final = 8
EMBEDDING_MODEL_ID: Final = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIM: Final = 256
EMBEDDING_NORMALIZE: Final = True
SPEND_CAP_USD: Final = 25.00
LLM_INPUT_PRICE_PER_1M: Final = 0.10
LLM_CACHED_INPUT_PRICE_PER_1M: Final = 0.01
LLM_OUTPUT_PRICE_PER_1M: Final = 0.50
SELF_CONSISTENCY_SAMPLE: Final = 200
SELF_CONSISTENCY_THRESHOLD: Final = 0.90
S3_BUCKET: Final = "mirrorview-experimental-artifacts"
S3_PREFIX: Final = "experiments/llm_feature_generation_phase_2_part_3_2026_09_24/"
RUN_TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H-%M-%S"
COST_LOG_PATH: Final = "outputs/shared/cost_log.jsonl"
PART2_STAGE2_OUTPUT_DIR: Final = (
    "experiments/llm_based_feature_generation_2026_07_31/"
    "outputs/2026_08_01-14:08:32.373981/"
)
MIN_RATERS: Final = 4
SPLIT_VOTE_PATTERNS: Final = frozenset({(2, 2), (3, 2), (2, 3)})
GROUP_SPLIT: Final = "split"
GROUP_UNANIMOUS_KEEP: Final = "unanimous_keep"
GROUP_UNANIMOUS_REMOVE: Final = "unanimous_remove"
DECISION_KEEP: Final = "keep"
DECISION_REMOVE: Final = "remove"
EVALUATION_MODE_LINKED_FATE: Final = "linked_fate"
TRIAL_TYPE_MODERATION: Final = "moderation-trial"
EMPTY_POST_SENTINEL: Final = "nan"
PARTICIPANT_FILTER_ALL: Final = "all"
PARTICIPANT_FILTER_ATTENTION_PASS: Final = "attention_pass"
PHASE_ONE: Final = 1
COHORT_FILENAME: Final = "cohort.parquet"
METADATA_FILENAME: Final = "metadata.json"
DISCOVERY_SPLIT: Final = "discovery"
TEST_SPLIT: Final = "test"
UNLABELED_STRATUM: Final = "unlabeled"
STRATIFY_MARGIN: Final = 0.05
TEST_SIZE: Final = 0.5
EXPECTED_POST_COUNT: Final = 18899
EXPECTED_LABELED_COUNT: Final = 18866
EXPECTED_PART2_OVERLAP: Final = 8899
EXPECTED_LABEL_COUNT_ONE: Final = 1145
EXPECTED_LABEL_COUNT_TWO: Final = 1755
EXPECTED_LABEL_COUNT_THREE_PLUS: Final = 15966
EXPECTED_DISCOVERY_COUNT: Final = 9449
EXPECTED_TEST_COUNT: Final = 9450
TOXICITY_PREFIX: Final = "sample_"
TOXICITY_SUFFIX: Final = "_toxicity"
REQUIRED_SLIM_COLUMNS: Final = (
    "evaluation_mode",
    "decision",
    "post_id",
    "prolific_id",
    "trial_type",
    "phase",
    "time_elapsed",
    "trial_index",
    "attention_check_passed",
)
STRATIFY_COLUMNS: Final = (
    "modal_decision",
    "sampled_stance",
    "sample_toxicity_type",
    "in_part2_catalog",
)
COHORT_COLUMNS: Final = (
    "post_id",
    "original_text",
    "mirror_text",
    "modal_decision",
    "keep_count",
    "remove_count",
    "n_raters",
    "three_group_label",
    "sampled_stance",
    "sample_toxicity_type",
    "in_part2_catalog",
    "split",
    "participant_filter",
)
