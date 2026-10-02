"""Build and upload the balanced 405-post cohort.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step1_setup/main.py
"""

from __future__ import annotations

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.artifacts import MANIFEST_KEY, upload_inputs
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.config import (
    S3_BUCKET,
    SPLIT_KEEP_COUNTS,
    SPLIT_NAMES,
    SPLIT_REMOVE_COUNTS,
)
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.data import build_balanced_splits


def main() -> None:
    """Validate the balanced cohort and write it to S3."""
    bundle = build_balanced_splits()
    hashes = upload_inputs(bundle)
    print("eligible_rows", bundle.eligible_count)
    print("cohort_rows", len(bundle.cohort_ids))
    for name in SPLIT_NAMES:
        print("split", name, "keep", SPLIT_KEEP_COUNTS[name], "remove", SPLIT_REMOVE_COUNTS[name])
    print("manifest_uri", f"s3://{S3_BUCKET}/{MANIFEST_KEY}")
    for key, digest in hashes.items():
        print("sha256", digest, key)


if __name__ == "__main__":
    main()
