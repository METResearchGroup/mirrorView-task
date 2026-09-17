"""Configuration for the Reddit Pushshift toxicity experiment.

This module centralizes thresholds, API pacing knobs, and filesystem roots used
by the extraction and scoring pipeline.
"""

from pathlib import Path

# Modules live under ``src/``, but data, outputs, scripts, and runbooks live at
# the experiment root one level above it.
EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent

MIN_BODY_LEN = 20
MAX_BODY_LEN = 300
TOXICITY_THRESHOLD = 0.7
GLOBAL_STOP_COUNT = 50_000
MAX_SESSION_API_CALLS = 1_000_000
PERSPECTIVE_BATCH_SIZE = 90
PERSPECTIVE_DELAY_SECONDS = 1.05
PERSPECTIVE_MAX_RETRIES = 4
DELETED_TOKENS = {"[deleted]", "[removed]"}
INPUT_GLOB = "data/raw/**/RC_*.zst"
MAX_FILES_TO_PROCESS: int | None = 10

OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
RAW_DATA_DIR = EXPERIMENT_ROOT / "data" / "raw"
BOLUN_DATA_DIR = EXPERIMENT_ROOT / "data" / "bolun"
BOLUN_TARBALL = BOLUN_DATA_DIR / "bolun_package.tar.zst"
BOLUN_EXTRACTED_DIR = BOLUN_DATA_DIR / "extracted"
BOLUN_INVENTORY_PATH = BOLUN_DATA_DIR / "inventory.json"
BOLUN_STAGED_DIR = RAW_DATA_DIR / "bolun" / "comments"
BOLUN_DRIVE_FILE_ID = "17412qQBz9UTkDGCO0F-vHjWMkJNOdTgh"
