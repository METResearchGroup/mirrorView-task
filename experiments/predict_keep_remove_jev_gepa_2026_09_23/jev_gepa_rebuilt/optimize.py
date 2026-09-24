"""GEPA optimize runner stub for rebuilt union cohort runs.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

ABLATION_IDS = (
    "R1_gepa_pair",
    "R2_majority_weighted",
    "R3_gepa_pair_terra",
    "R4_gepa_multi_component",
    "R5_gepa_original",
    "R6_gepa_mirror",
    "R7_plain_majority",
)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for rebuilt GEPA optimization (stub until Step 3)."""
    parser = argparse.ArgumentParser(description="Run rebuilt Jev GEPA prompt optimization")
    parser.add_argument("--ablation-id", required=True, choices=sorted(ABLATION_IDS))
    parser.add_argument("--smoke", action="store_true", help="Run tiny-budget smoke configuration")
    parser.add_argument(
        "--max-metric-calls",
        type=int,
        default=None,
        help="Override max_metric_calls for the run",
    )
    parser.parse_args(argv)
    print("jev_gepa_rebuilt optimize stub")


if __name__ == "__main__":
    main(sys.argv[1:])
