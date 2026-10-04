"""Score the locked prompts once on the balanced test split.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step3_evaluate/main.py --run-id study2-gepa-balanced-2026-10-02-pilot
"""

from __future__ import annotations

import argparse

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.optimize import run_test


def main() -> None:
    """Evaluate the original and selected instructions."""
    args = _parse_args()
    run_test(args.run_id)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the balanced-cohort test split.")
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
