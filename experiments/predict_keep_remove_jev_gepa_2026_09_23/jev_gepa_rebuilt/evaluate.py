"""GEPA evaluate runner stub for rebuilt union cohort runs.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py --ablation-id R1_gepa_pair --split test
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

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import ABLATION_IDS


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for rebuilt GEPA evaluation (stub until later steps)."""
    parser = argparse.ArgumentParser(description="Run rebuilt Jev GEPA evaluation")
    parser.add_argument("--ablation-id", required=True, choices=sorted(ABLATION_IDS))
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.parse_args(argv)
    print("jev_gepa_rebuilt evaluate stub")


if __name__ == "__main__":
    main(sys.argv[1:])
