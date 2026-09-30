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
CLUSTER_NAMING_SAMPLE_SIZE = 50
LABEL_KEY_PREFIX = "is_"
NAMING_SMOKE_KEY = "step5_name_clusters/smoke_cluster_names.jsonl"
NAMING_ESTIMATES_KEY = "step5_name_clusters/estimates.json"
CLUSTER_NAMES_KEY = "step5_name_clusters/cluster_names.jsonl"
FEATURE_REVIEW_KEY = "step5_name_clusters/feature_review.csv"
JEV_MODEL_ID = "jev-1.13.0"
JEV_SECRET_ID = "jev-typesafe-api-key"
JEV_STATE_KEY = "pair"
JEV_REQUEST_TIMEOUT_SECONDS = 120.0
JEV_MAX_WORKERS = 8
JEV_MAX_REQUESTS_PER_MINUTE = 1000
JEV_RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
MAX_FEATURES_PER_JEV_REQUEST = 60
JEV_USD_PER_MILLION_INPUT = 0.042
JEV_USD_PER_MILLION_OUTPUT = 0.0
FEATURE_PRESENT_THRESHOLD = 0.7
LABEL_COLUMNS_PREFIX = ("post_id", "original_text", "mirror_text")
LABELING_SMOKE_KEY = "step6_label_posts_with_features/smoke_jev_predictions.jsonl"
LABELING_ESTIMATES_KEY = "step6_label_posts_with_features/estimates.json"
JEV_PREDICTIONS_KEY = "step6_label_posts_with_features/jev_predictions.jsonl"
JEV_DEADLETTER_KEY = "step6_label_posts_with_features/deadletter.jsonl"
JEV_PROBABILITIES_KEY = "step6_label_posts_with_features/jev_probabilities.parquet"
POST_FEATURE_LABELS_KEY = "step6_label_posts_with_features/post_feature_labels.parquet"
STANCE_LEVELS = ("left", "right")
TOXICITY_LEVELS = {
    "sample_low_toxicity": "low",
    "sample_middle_toxicity": "medium",
    "sample_high_toxicity": "high",
}
REMOVE_VOTE_LEVELS = (0, 1, 2, 3, 4, 5)
EXPECTED_STANCE_COUNTS = {"left": 11550, "right": 8450}
EXPECTED_TOXICITY_COUNTS = {"low": 5000, "medium": 10000, "high": 5000}
EXPECTED_REMOVE_VOTE_COUNTS = {0: 3986, 1: 4592, 2: 3332, 3: 1929, 4: 950, 5: 324}
TOP_FEATURES_PER_GROUP = 10
EVIDENT_CHARTS_SCRIPTS_DIR = Path("/tmp/evident-charts/skills/evident-charts/scripts")
CHART_PRESET = "blog"
CHART_SOURCE = "Source: MirrorView Study 2, Jev labels at a 0.7 cutoff"
ANALYSES_PREFIX = "analyses/"
TOP_BY_LEAN_KEY = "analyses/top_features_by_lean.csv"
TOP_BY_TOXICITY_KEY = "analyses/top_features_by_toxicity.csv"
TOP_BY_REMOVE_VOTES_KEY = "analyses/top_features_by_remove_votes.csv"
PAGE_PATH = REPO_ROOT / "public" / "study-2-features.html"
PAGE_KEY = "step7_analyze_post_features/study-2-features.html"
LEAN_CHART_KEY = "step7_analyze_post_features/figures/lean.svg"
TOXICITY_CHART_KEY = "step7_analyze_post_features/figures/toxicity.svg"
TOXICITY_PROPORTION_KEY = "analyses/feature_proportions_by_toxicity.csv"
REMOVE_VOTE_PROPORTION_KEY = "analyses/feature_proportions_by_remove_votes.csv"
TOXICITY_PROPORTION_CHART_KEY = "step7_analyze_post_features/figures/toxicity_proportions.svg"
REMOVE_VOTE_PROPORTION_CHART_KEY = "step7_analyze_post_features/figures/remove_votes_proportions.svg"

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.label_to_detail import (  # noqa: E402
    LABEL_TO_DETAIL,
)
