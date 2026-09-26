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
KMEANS_N_INIT: Final = 10
KMEANS_MAX_ITER: Final = 300
KMEANS_NARROW_K_MIN: Final = 2
KMEANS_NARROW_K_MAX: Final = 10
KMEANS_WIDE_K_MIN: Final = 10
KMEANS_WIDE_K_MAX: Final = 80
KMEANS_WIDE_K_STEP: Final = 5
HDBSCAN_DEFAULT_MIN_CLUSTER_SIZE: Final = 5
HDBSCAN_SUBSAMPLE_FRACTION: Final = 0.9
HDBSCAN_SUBSAMPLE_REPEATS: Final = 10
HDBSCAN_REFERENCE_SEED: Final = 42
NOISE_CLUSTER_ID: Final = -1
STABILITY_V2_FILENAME: Final = "stability_v2.json"
K_SELECTION_WIDE_FILENAME: Final = "k_selection_wide.json"
STABILITY_ACROSS_ARMS_V2_FILENAME: Final = "stability_across_arms_v2.json"
TEXT_ARMS: Final = ("original_only", "mirror_only", "paired")
BATCH_DESIGN_MIXED: Final = "mixed"
BATCH_DESIGN_MIXED_TOPUP: Final = "mixed_topup"
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
PARTICIPANT_FILTER_PART3_ONLY: Final = "part3_only"
COLLECTION_PART2: Final = "part2"
COLLECTION_PART3: Final = "part3"
DATASET_PHASE_2_PART_2_AND_3: Final = "phase_2_part_2_and_3"
PHASE_ONE: Final = 1
COHORT_FILENAME: Final = "cohort.parquet"
METADATA_FILENAME: Final = "metadata.json"
DISCOVERY_SPLIT: Final = "discovery"
TEST_SPLIT: Final = "test"
UNLABELED_STRATUM: Final = "unlabeled"
RARE_STRATIFY_BUCKET: Final = "rare_stratum"
STRATIFY_MARGIN: Final = 0.05
TEST_SIZE: Final = 0.5
EXPECTED_POST_COUNT: Final = 20000
EXPECTED_LABELED_COUNT: Final = 20000
EXPECTED_PART2_OVERLAP: Final = 10000
EXPECTED_NEW_POST_COUNT: Final = 1101
EXPECTED_LABEL_COUNT_ONE: Final = 0
EXPECTED_LABEL_COUNT_TWO: Final = 0
EXPECTED_LABEL_COUNT_THREE_PLUS: Final = 20000
EXPECTED_THREE_GROUP_ELIGIBLE: Final = 10761
EXPECTED_THREE_GROUP_SPLIT: Final = 5217
EXPECTED_THREE_GROUP_UNANIMOUS_KEEP: Final = 5126
EXPECTED_THREE_GROUP_UNANIMOUS_REMOVE: Final = 418
EXPECTED_MODAL_KEEP_RATE: Final = 0.7570
LEGACY_PART3_POST_COUNT: Final = 18899
LEGACY_DISCOVERY_COUNT: Final = 9449
LEGACY_TEST_COUNT: Final = 9450
EXPECTED_DISCOVERY_COUNT: Final = 9999
EXPECTED_TEST_COUNT: Final = 10001
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
CODEBOOK_EXAMPLES_PER_POLARITY: Final = 2
CODEBOOK_NAME_MIN_WORDS: Final = 2
CODEBOOK_NAME_MAX_WORDS: Final = 6
CODEBOOK_REWRITE_BATCH_SIZE: Final = 15
STAGE_CODEBOOK_REWRITE: Final = "codebook_rewrite"
MERGE_CANDIDATES_FILENAME: Final = "merge_candidates.csv"
MERGE_BORDERLINE_MIN_COSINE: Final = 0.80
CODEBOOK_FEATURE_ID_PREFIX: Final = "cb_"
CODEBOOK_DRAFT_DIR_PREFIX: Final = "draft_"
CODEBOOK_APPROVED_DIR_PREFIX: Final = "approved_"
CODEBOOK_FINAL_DIR_PREFIX: Final = "final_"
GATE_B_APPROVED_BY: Final = "user"
CODEBOOK_MERGE_SIMILARITY_THRESHOLD: Final = 0.85
FEATURE_SYNONYMS_FILENAME: Final = "feature_synonyms.csv"
ASSIGNMENTS_HDBSCAN_FILENAME: Final = "assignments_hdbscan.json"
CLUSTER_SEED_DIR_TEMPLATE: Final = "clusters_seed_{seed}"
NOISE_CLUSTER_ID: Final = -1
CODEBOOK_JSON_FILENAME: Final = "codebook.json"
CODEBOOK_MD_FILENAME: Final = "codebook.md"
DROPPED_FEATURES_FILENAME: Final = "dropped_features.json"
APPROVAL_JSON_FILENAME: Final = "approval.json"
OPERATIONALIZE_CLUSTERS_FILENAME: Final = "clusters.jsonl"
TOPIC_ONLY_CATEGORY: Final = "topic_subject"
TOPIC_ONLY_POLICY_TERMS: Final = (
    "guns",
    "gun",
    "immigration",
    "abortion",
    "climate",
    "election",
)
OUTCOME_LEAKAGE_TERMS: Final = ("keep", "remove", "moderat", "rated", "cluster")
DEFINITION_REQUIRED_PREFIX: Final = "The post"
