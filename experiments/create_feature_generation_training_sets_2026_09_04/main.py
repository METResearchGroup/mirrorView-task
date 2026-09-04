"""CLI for building per-classifier feature-generation training parquets.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/create_feature_generation_training_sets_2026_09_04/main.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lib.timestamp_utils import get_current_timestamp

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    DEFAULT_DATA_ROOT,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.paths import (
    experiment_root,
    training_data_root,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.summary import (
    collect_file_stats,
    write_summary,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.upload import (
    upload_training_parquets,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.walk import (
    build_training_sets,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the training-set build command.

    Parameters
    ----------
    argv
        Optional argument list; defaults to ``sys.argv`` when omitted.

    Returns
    -------
    argparse.Namespace
        Parsed ``--data-root``, ``--output-root``, ``--timestamp``, and ``--upload``.
    """
    parser = argparse.ArgumentParser(
        description="Build per-classifier training parquets from feature labels.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root folder containing platform dataset directories.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=training_data_root(),
        help="Local root for per-classifier training parquet outputs.",
    )
    parser.add_argument(
        "--timestamp",
        default=get_current_timestamp(),
        help="UTC timestamp stamped on every output parquet filename.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload built parquets to S3 after the local build completes.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=experiment_root() / "SUMMARY.md",
        help="Destination path for SUMMARY.md after upload.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build training parquets from classifier labels and preprocessed records.

    Parameters
    ----------
    argv
        Optional argument list forwarded to :func:`parse_args`.

    Returns
    -------
    int
        Process exit code; ``0`` on success.
    """
    args = parse_args(argv)
    paths = build_training_sets(
        args.data_root,
        timestamp=args.timestamp,
        output_root=args.output_root,
    )
    if args.upload:
        upload_training_parquets(paths, args.output_root)
        stats = collect_file_stats(paths, args.output_root)
        write_summary(stats, args.summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
