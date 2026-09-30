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
LLM_MODEL = "gpt-5.6-terra"
LLM_TEMPERATURE = 1.0
LLM_CONCURRENCY = 8
LLM_USD_PER_MILLION_INPUT = 2.00
LLM_USD_PER_MILLION_OUTPUT = 12.00
AWS_SECRETS_REGION = "us-east-2"
OPENAI_SECRET_ID = "openai-api-key"
FEATURE_CATEGORIES = (
    "lexical",
    "topic_subject",
    "semantic_content",
    "pragmatics",
    "target",
    "structure",
)
FEATURE_SIDES = ("features_from_kept_posts", "features_from_removed_posts")
MINING_SMOKE_KEY = "step2_mine_candidate_features/smoke_candidate_features.jsonl"
MINING_ESTIMATES_KEY = "step2_mine_candidate_features/estimates.json"
CANDIDATE_FEATURES_KEY = "step2_mine_candidate_features/candidate_features.jsonl"
SIDE_KEPT = "kept"
SIDE_REMOVED = "removed"
EMBED_MAX_WORKERS = 8
EMBED_THROTTLE_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
TITAN_USD_PER_MILLION_TOKENS = 0.02
FEATURES_KEY = "step3_embed_features/features.parquet"
EMBEDDINGS_KEY = "step3_embed_features/embeddings.npy"
FEATURE_IDS_KEY = "step3_embed_features/feature_ids.json"
KMEANS_CLUSTERS_PER_SIDE = 15
CLUSTER_ID_WIDTH = 3
ASSIGNMENTS_KEY = "step4_cluster_records/assignments.parquet"
CLUSTER_SIZES_KEY = "step4_cluster_records/cluster_sizes.parquet"
CLUSTER_METADATA_KEY = "step4_cluster_records/metadata.json"
