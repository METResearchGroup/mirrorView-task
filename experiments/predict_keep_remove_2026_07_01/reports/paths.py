"""Path helpers for the reports package."""

from __future__ import annotations

from pathlib import Path

from lib.timestamp_utils import get_current_timestamp

# reports/ -> experiment root (predict_keep_remove_2026_07_01/)
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS_MD = EXPERIMENT_ROOT / "results.md"
DEFAULT_OUTPUTS_DIR = REPORTS_ROOT / "outputs"
DEFAULT_EMBEDDING_CACHE_DIR = EXPERIMENT_ROOT / "embedding_cache"


def make_output_dir(outputs_name: str) -> Path:
    """Create ``reports/outputs/<outputs_name>/<timestamp>/``."""
    out_dir = DEFAULT_OUTPUTS_DIR / outputs_name / get_current_timestamp()
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir
