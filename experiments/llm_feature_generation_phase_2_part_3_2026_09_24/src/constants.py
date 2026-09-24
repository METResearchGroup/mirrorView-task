"""Pinned constants for the Phase 2 Part 3 LLM feature experiment.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
    print(constants.SPLIT_SEED)
    "
"""

from __future__ import annotations

LLM_MODEL_ID = "gpt-6-luna"
LLM_LITELLM_MODEL_ID = "openai/gpt-6-luna"
LLM_REASONING_EFFORT = "none"
SPLIT_SEED = 42
CLUSTER_SEEDS = (42, 43, 44)
DEFAULT_SEED = 42
TEXT_ARMS = ("original_only", "mirror_only", "paired")
BATCH_DESIGN_MIXED = "mixed"
BATCH_DESIGN_SINGLE_CLASS = "single_class"
MAX_KEEP_FEATURES_PER_BATCH = 8
MAX_REMOVE_FEATURES_PER_BATCH = 8
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIM = 256
EMBEDDING_NORMALIZE = True
SPEND_CAP_USD = 25.00
LLM_INPUT_PRICE_PER_1M = 0.10
LLM_CACHED_INPUT_PRICE_PER_1M = 0.01
LLM_OUTPUT_PRICE_PER_1M = 0.50
SELF_CONSISTENCY_SAMPLE = 200
SELF_CONSISTENCY_THRESHOLD = 0.90
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = "experiments/llm_feature_generation_phase_2_part_3_2026_09_24/"
RUN_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"
COST_LOG_PATH = "outputs/shared/cost_log.jsonl"
PART2_STAGE2_OUTPUT_DIR = (
    "experiments/llm_based_feature_generation_2026_07_31/"
    "outputs/2026_08_01-14:08:32.373981/"
)
MIN_RATERS = 4
SPLIT_VOTE_PATTERNS = frozenset({(2, 2), (3, 2), (2, 3)})
GROUP_SPLIT = "split"
GROUP_UNANIMOUS_KEEP = "unanimous_keep"
GROUP_UNANIMOUS_REMOVE = "unanimous_remove"
