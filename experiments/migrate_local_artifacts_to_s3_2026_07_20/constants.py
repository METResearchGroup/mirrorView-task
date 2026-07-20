"""Shared constants for experiment artifact S3 migration tooling."""

from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]  # .../mirrorView-task

BUCKET = "mirrorview-experimental-artifacts"
DEFAULT_REGION = "us-east-2"

DB_PATH = EXPERIMENT_DIR / "migration_tracker.db"
UPLOAD_SCRIPT = EXPERIMENT_DIR / "upload_to_s3.sh"
VERIFY_SCRIPT = EXPERIMENT_DIR / "verify_s3_object.sh"
INVENTORY_DIR = EXPERIMENT_DIR / "inventory"
MANIFESTS_DIR = EXPERIMENT_DIR / "manifests"

# Default allowlist: the 9 folders with csv/json in AFFECTED_FILES.md
EXPERIMENT_ALLOWLIST: tuple[str, ...] = (
    "experiments/fetch_reddit_pushshift_dump_2026_06_15",
    "experiments/followup_model_error_analysis_2026_07_15",
    "experiments/mirrors_content_analysis_2026_04_24",
    "experiments/model_errors_analysis_2026_07_15",
    "experiments/predict_keep_remove_2026_05_07",
    "experiments/predict_keep_remove_2026_07_01",
    "experiments/scaled_mirrors_generation_2026_06_02",
    "experiments/simplified_predict_remove_2026_05_13",
    "experiments/truncate_posts_2026_06_19",
)

# Always skip these path fragments (matched against repo-relative POSIX path)
EXCLUDE_PATH_SUBSTRINGS: tuple[str, ...] = (
    "experiments/migrate_local_artifacts_to_s3_2026_07_20/",
    "/__pycache__/",
    "/.git/",
)

INCLUDE_SUFFIXES: tuple[str, ...] = (".csv", ".json")

# Empty files (size == 0) register as skipped
SKIP_EMPTY_FILES: bool = True
