"""Shared paths for original-vs-mirrored Titan embedding PCA/LDA analysis."""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
ANALYSIS_DIR = OUTPUTS_DIR / "analysis"

ANALYSIS_META_PATH = ANALYSIS_DIR / "analysis_meta.csv"
ANALYSIS_TABLE_PATH = ANALYSIS_DIR / "analysis_table.parquet"
EMBEDDING_MATRIX_PATH = ANALYSIS_DIR / "X_original_and_mirror.npy"
PROGRESS_UPDATES_PATH = ANALYSIS_DIR / "progress_updates.md"
PROGRESS_UPDATES_VIZ_PATH = ANALYSIS_DIR / "progress_updates_viz.md"
PCA_PLOT_PATH = ANALYSIS_DIR / "pca_original_vs_mirrored.png"
LDA_PLOT_PATH = ANALYSIS_DIR / "lda_original_vs_mirrored.png"
EMBEDDINGS_2D_PATH = ANALYSIS_DIR / "embeddings_2d.csv"
REDUCTION_SUMMARY_PATH = ANALYSIS_DIR / "reduction_summary.json"
PCA_VARIANCE_PATH = ANALYSIS_DIR / "pca_variance_explained.json"

PKR_ROOT = REPO_ROOT / "experiments" / "predict_keep_remove_2026_07_01"
WORKTREE_EMBEDDING_CACHE = PKR_ROOT / "embedding_cache"
# Optional backup only — happy path uses the worktree cache (local .npy; no S3).
MAIN_REPO_EMBEDDING_CACHE = (
    Path("/Users/mark/Documents/work/mirrorView-task")
    / "experiments"
    / "predict_keep_remove_2026_07_01"
    / "embedding_cache"
)

FEATURE_SET = "original_and_mirror_long"
EMBEDDING_DIM = 256
LDA_TARGET = "is_mirrored"
