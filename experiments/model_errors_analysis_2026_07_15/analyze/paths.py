"""Shared paths for right/wrong analysis artifacts (Qwen labels + Titan features)."""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
LABELS_CSV_PATH = OUTPUTS_DIR / "base_model_llm_labels.csv"

ANALYSIS_DIR = OUTPUTS_DIR / "analysis"
ANALYSIS_TABLE_PATH = ANALYSIS_DIR / "analysis_table.parquet"
ANALYSIS_META_PATH = ANALYSIS_DIR / "analysis_meta.csv"
EMBEDDING_MATRIX_PATH = ANALYSIS_DIR / "X_only_original.npy"
SPLIT_IDS_PATH = ANALYSIS_DIR / "split_ids.json"
PROGRESS_UPDATES_PATH = ANALYSIS_DIR / "progress_updates.md"
PROGRESS_UPDATES_VIZ_PATH = ANALYSIS_DIR / "progress_updates_viz.md"
PCA_PLOT_PATH = ANALYSIS_DIR / "pca_right_vs_wrong.png"
LDA_PLOT_PATH = ANALYSIS_DIR / "lda_right_vs_wrong.png"
EMBEDDINGS_2D_PATH = ANALYSIS_DIR / "embeddings_2d.csv"
REDUCTION_SUMMARY_PATH = ANALYSIS_DIR / "reduction_summary.json"
PROGRESS_UPDATES_TRAIN_PATH = ANALYSIS_DIR / "progress_updates_train.md"

# Linear separator artifacts
LINEAR_SEPARATOR_METRICS_PATH = ANALYSIS_DIR / "linear_separator_metrics.json"
LOGISTIC_METRICS_PATH = ANALYSIS_DIR / "logistic_metrics.json"  # alias
LINEAR_SEPARATOR_MODEL_PATH = ANALYSIS_DIR / "linear_separator_model.joblib"
LINEAR_SEPARATOR_COEFS_PATH = ANALYSIS_DIR / "linear_separator_coefficients.csv"
LINEAR_SEPARATOR_PREDS_PATH = ANALYSIS_DIR / "linear_separator_predictions.csv"

# Reduced-space clustering artifacts
CLUSTERS_DIR = ANALYSIS_DIR / "clusters"
CLUSTER_ASSIGNMENTS_PATH = CLUSTERS_DIR / "cluster_assignments.csv"
CLUSTER_METRICS_JSON_PATH = CLUSTERS_DIR / "cluster_metrics.json"
CLUSTER_METRICS_CSV_PATH = CLUSTERS_DIR / "cluster_lift_table.csv"
CLUSTER_K_SELECTION_PATH = CLUSTERS_DIR / "k_selection.json"
CLUSTER_PLOT_PATH = CLUSTERS_DIR / "pca2d_by_cluster.png"
CLUSTER_EXEMPLARS_PATH = CLUSTERS_DIR / "cluster_exemplars.md"
CLUSTER_EXEMPLARS_CSV_PATH = CLUSTERS_DIR / "cluster_exemplars.csv"
CLUSTER_PROGRESS_PATH = CLUSTERS_DIR / "progress_updates.md"
CLUSTER_MODEL_PATH = CLUSTERS_DIR / "kmeans_pca_model.joblib"

PKR_ROOT = REPO_ROOT / "experiments" / "predict_keep_remove_2026_07_01"
WORKTREE_EMBEDDING_CACHE = PKR_ROOT / "embedding_cache"
# Populated cache from the main checkout (gitignored; shared across worktrees).
MAIN_REPO_EMBEDDING_CACHE = (
    Path("/Users/mark/Documents/work/mirrorView-task")
    / "experiments"
    / "predict_keep_remove_2026_07_01"
    / "embedding_cache"
)

PRIMARY_CLASSIFIER_ID = "bedrock/qwen3-next-80b-a3b"
FEATURE_SET = "only_original"
EMBEDDING_DIM = 256
SPLIT_SEED = 42
TRAIN_SPLIT = 0.8
STRATIFY_ON = "is_error"
