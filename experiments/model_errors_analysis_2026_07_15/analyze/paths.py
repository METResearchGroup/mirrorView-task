"""Shared paths for V1 Bedrock right/wrong analysis artifacts."""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
LABELS_CSV_PATH = OUTPUTS_DIR / "base_model_llm_labels.csv"

V1_DIR = OUTPUTS_DIR / "v1_bedrock"
ANALYSIS_TABLE_PATH = V1_DIR / "analysis_table.parquet"
ANALYSIS_META_PATH = V1_DIR / "analysis_meta.csv"
EMBEDDING_MATRIX_PATH = V1_DIR / "X_only_original.npy"
SPLIT_IDS_PATH = V1_DIR / "split_ids.json"
PROGRESS_UPDATES_PATH = V1_DIR / "progress_updates.md"
PROGRESS_UPDATES_VIZ_PATH = V1_DIR / "progress_updates_viz.md"
PCA_PLOT_PATH = V1_DIR / "pca_right_vs_wrong.png"
LDA_PLOT_PATH = V1_DIR / "lda_right_vs_wrong.png"
EMBEDDINGS_2D_PATH = V1_DIR / "embeddings_2d.csv"
REDUCTION_SUMMARY_PATH = V1_DIR / "reduction_summary.json"
PROGRESS_UPDATES_TRAIN_PATH = V1_DIR / "progress_updates_train.md"

# V1.3A logistic separator artifacts
LINEAR_SEPARATOR_METRICS_PATH = V1_DIR / "linear_separator_metrics.json"
LOGISTIC_METRICS_PATH = V1_DIR / "logistic_metrics.json"  # alias
LINEAR_SEPARATOR_MODEL_PATH = V1_DIR / "linear_separator_model.joblib"
LINEAR_SEPARATOR_COEFS_PATH = V1_DIR / "linear_separator_coefficients.csv"
LINEAR_SEPARATOR_PREDS_PATH = V1_DIR / "linear_separator_predictions.csv"

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
