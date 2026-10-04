"""Run the balanced-cohort GEPA pilot.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step2_optimize/main.py --run-id study2-gepa-balanced-2026-10-02-pilot --max-metric-calls 1000
"""

from __future__ import annotations

import argparse

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.optimize import run_pilot


def main() -> None:
    """Optimize and lock one instruction on the balanced cohort."""
    args = _parse_args()
    run_pilot(args.run_id, args.max_metric_calls)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize the instruction on the balanced cohort.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-metric-calls", type=int, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
