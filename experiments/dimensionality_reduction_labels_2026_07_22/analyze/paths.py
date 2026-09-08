"""Shared paths for human keep/remove PCA/LDA visualization (exploratory full-data fit)."""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
ANALYSIS_DIR = OUTPUTS_DIR / "analysis"
LABELS_CSV_PATH = (
    REPO_ROOT
    / "experiments/model_errors_analysis_2026_07_15/outputs/base_model_llm_labels.csv"
)
ANALYSIS_META_PATH = ANALYSIS_DIR / "analysis_meta.csv"
ANALYSIS_TABLE_META_PATH = ANALYSIS_DIR / "analysis_table_meta.json"
X_ORIGINAL_PATH = ANALYSIS_DIR / "X_original.npy"
X_MIRRORED_PATH = ANALYSIS_DIR / "X_mirrored.npy"
ORIGINAL_DIR = ANALYSIS_DIR / "original"
MIRRORED_DIR = ANALYSIS_DIR / "mirrored"
BOTH_DIR = ANALYSIS_DIR / "both"

PKR_ROOT = REPO_ROOT / "experiments" / "predict_keep_remove_2026_07_01"
WORKTREE_EMBEDDING_CACHE = PKR_ROOT / "embedding_cache"
MAIN_REPO_EMBEDDING_CACHE = (
    Path("/Users/mark/Documents/work/mirrorView-task")
    / "experiments"
    / "predict_keep_remove_2026_07_01"
    / "embedding_cache"
)

EMBEDDING_DIM = 256
FEATURE_SET_ORIGINAL = "only_original"
FEATURE_SET_MIRRORED = "only_mirrored"
FEATURE_SET_BOTH = "original_and_mirrored_stacked"
FIT_REGIME = "full_data_exploratory"  # not train-only; viz only
