"""Run flip generation on the pinned unified 2,300 post upsample.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned unified parquet exists at 2300 rows
when PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id smoke --max-posts 10
then part_count=1
and row_count + failed_count = 10
and S3 object experiments/generate_flips_for_upsampled_posts_2026_09_08/smoke/batches/part-00000.parquet exists
and the named sibling key is absent

given the same smoke command is run again
then existing smoke parts are not rewritten

given a new timestamp --run-id and no --max-posts
when the command runs
then row_count + failed_count = 2300
and S3 object experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet exists

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --help
"""

from __future__ import annotations

import sys

import typer

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_flips_for_upsampled_posts_2026_09_08.load_unified_dataset import (
    load_unified_dataset,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    NamedFlipCopyResult,
    pinned_unified_source,
)
from shared.flip_generation.models import FlipRunResult


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    run_id: str = typer.Option(
        "",
        "--run-id",
        help="S3 run folder name. The 10-post test uses smoke.",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        help="Limit rows after load. The 10-post test uses 10.",
    ),
    bucket: str = typer.Option("", "--bucket"),
) -> None:
    """Load the pinned unified parquet and generate mirrored posts.

    Parameters
    ----------
    run_id
        S3 run folder name. Defaults to the current timestamp when omitted.
    max_posts
        When set, only the first N loaded rows are flipped.
    bucket
        S3 bucket for flip output artifacts.
    """
    raise NotImplementedError


def copy_named_sibling_flips(
    result: FlipRunResult,
    store: CampaignObjectStore,
) -> NamedFlipCopyResult:
    """Copy concatenated flips to the named sibling key after a full run.

    Parameters
    ----------
    result
        Full-run flip result with ``wrote_final`` true.
    store
        Object store used only with ``put_new`` for the named key.

    Returns
    -------
    NamedFlipCopyResult
        Named S3 URI and SHA-256.

    Raises
    ------
    FileExistsError
        When the named sibling key already exists.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(app())
