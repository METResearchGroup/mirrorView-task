"""Stage 2: embed Stage-1 feature texts via shared feature_discovery helpers.

Run from repo root::

    PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py \\
      --likert-group low \\
      --features-run-dir experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/generated_features/low/outputs/<TIMESTAMP>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.paths import (
    LikertGroup,
    latest_timestamp_subdir,
    stage1_root,
    stage2_root,
    validate_likert_group,
)
from shared.feature_discovery.llm_based.embed_features import run_embed_features
from shared.feature_discovery.llm_based.paths import make_run_timestamp


def resolve_features_run_dir(
    likert_group: str,
    features_run_dir: str | None,
) -> Path:
    """Resolve Stage-1 run directory from an explicit path or the latest timestamp.

    Parameters
    ----------
    likert_group
        low or high.
    features_run_dir
        Explicit Stage-1 timestamp directory, or None to pick latest.

    Returns
    -------
    Path
        Stage-1 run directory containing item JSON files.
    """
    if features_run_dir:
        path = Path(features_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"features-run-dir not found: {path}")
        return path
    outputs_parent = stage1_root(likert_group) / "outputs"
    return latest_timestamp_subdir(outputs_parent)


def run_generate_embeddings(
    likert_group: str,
    features_run_dir: str | None,
) -> Path:
    """Run Stage 2 for one Likert group and return the output directory.

    Parameters
    ----------
    likert_group
        low or high.
    features_run_dir
        Explicit Stage-1 directory or None for latest.

    Returns
    -------
    Path
        Stage-2 run directory.
    """
    validate_likert_group(likert_group)
    source_dir = resolve_features_run_dir(likert_group, features_run_dir)
    return run_embed_features(
        output_root=stage2_root(likert_group),
        label_class=likert_group,
        features_run_dir=source_dir,
        run_timestamp=make_run_timestamp(),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 2."""
    parser = argparse.ArgumentParser(
        description="Embed Stage-1 free-response feature texts with Amazon Titan."
    )
    parser.add_argument(
        "--likert-group",
        required=True,
        choices=[LikertGroup.LOW.value, LikertGroup.HIGH.value],
    )
    parser.add_argument(
        "--features-run-dir",
        default=None,
        help="Stage-1 timestamp dir; defaults to latest under stage1_root/outputs/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: embed Stage-1 features for one Likert group."""
    args = parse_args(argv)
    out_dir = run_generate_embeddings(args.likert_group, args.features_run_dir)
    print(f"Wrote Stage-2 embeddings to {out_dir}")


if __name__ == "__main__":
    main()
