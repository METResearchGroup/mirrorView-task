"""Evaluate the locked original and selected programs on the test split.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py --run-id RUN_ID
"""

from __future__ import annotations

import argparse
import json

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import S3_BUCKET, S3_PREFIX
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import apply_lab_aws_credentials
from lib.aws.s3 import S3


def main() -> None:
    """Refuse test evaluation until a pilot selection is locked."""
    args = _parse_args()
    apply_lab_aws_credentials()
    key = f"{S3_PREFIX}runs/{args.run_id}/selection/selected_program.json"
    store = S3(S3_BUCKET, region_name="us-east-2")
    if not store.object_exists(key):
        raise SystemExit(
            "selection is not locked. Approve the smoke run before the pilot, then evaluate."
        )
    payload = json.loads(store.get_bytes(key))
    if payload.get("selection_status") != "locked":
        raise SystemExit("selected_program.json is present but selection_status is not locked")
    raise SystemExit("locked selection found; test evaluation is not started in this build")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a locked DSPy GEPA run.")
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
