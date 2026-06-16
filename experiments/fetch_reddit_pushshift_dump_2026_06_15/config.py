"""Constants for the Academic Torrents Reddit toxicity smoke pipeline."""

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent

MIN_BODY_LEN = 20
MAX_BODY_LEN = 300
TOXICITY_THRESHOLD = 0.7
GLOBAL_STOP_COUNT = 50_000
MAX_SESSION_API_CALLS = 50_000
PERSPECTIVE_BATCH_SIZE = 90
PERSPECTIVE_DELAY_SECONDS = 1.05
PERSPECTIVE_MAX_RETRIES = 4
DELETED_TOKENS = {"[deleted]", "[removed]"}
INPUT_GLOB = "data/raw/**/RC_*.zst"
MAX_FILES_TO_PROCESS: int | None = 10

OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
RAW_DATA_DIR = EXPERIMENT_ROOT / "data" / "raw"
