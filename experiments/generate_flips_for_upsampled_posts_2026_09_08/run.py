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

import pandas as pd
import typer

from data_platform.generate_features.engines.bedrock_engine import (
    create_bedrock_runtime_client,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_flips_for_upsampled_posts_2026_09_08.load_unified_dataset import (
    load_unified_dataset,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    DEFAULT_CACHE_DIR,
    INPUT_S3_BUCKET,
    NamedFlipCopyResult,
    OUTPUT_S3_BUCKET,
    POST_COLUMNS,
    RUN_KEY_PREFIX,
    SMOKE_MAX_POSTS,
    SMOKE_RUN_ID,
    pinned_unified_source,
)
from lib.constants import DEFAULT_BEDROCK_SONNET_MODEL
from lib.timestamp_utils import get_current_timestamp
from shared.flip_generation.generate_flips import (
    BATCH_SIZE,
    MAX_CONCURRENCY,
    MAX_TOKENS,
    generate_flips,
)
from shared.flip_generation.models import FlipRunResult
import pandas as pd


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
    bucket: str = typer.Option(OUTPUT_S3_BUCKET, "--bucket"),
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
    resolved_run_id = run_id if run_id else get_current_timestamp()
    _require_smoke_is_not_full_run(resolved_run_id, max_posts)
    result = _generate_for_run(resolved_run_id, max_posts, bucket)
    _print_run_summary(result)


def _require_smoke_is_not_full_run(run_id: str, max_posts: int | None) -> None:
    if run_id == SMOKE_RUN_ID and max_posts is None:
        raise ValueError("do not reuse --run-id smoke for the full 2300 post job")


def _generate_for_run(
    run_id: str, max_posts: int | None, bucket: str
) -> FlipRunResult:
    run_prefix = f"{RUN_KEY_PREFIX}{run_id}/"
    posts = _posts_for_run(max_posts)
    return generate_flips(
        posts,
        CampaignObjectStore(bucket),
        run_prefix,
        create_bedrock_runtime_client(),
        BATCH_SIZE,
        MAX_CONCURRENCY,
        MAX_TOKENS,
        DEFAULT_BEDROCK_SONNET_MODEL,
    )


def _posts_for_run(max_posts: int | None) -> pd.DataFrame:
    source = pinned_unified_source()
    dataset = load_unified_dataset(
        source, CampaignObjectStore(INPUT_S3_BUCKET), DEFAULT_CACHE_DIR
    )
    posts = dataset.loc[:, list(POST_COLUMNS)]
    if max_posts is not None:
        return posts.head(max_posts)
    return posts


def _print_run_summary(result: FlipRunResult) -> None:
    print(f"run_prefix={result.run_prefix}")
    print(f"part_count={result.part_count}")
    print(f"row_count={result.row_count}")
    print(f"failed_count={result.failed_count}")
    print(f"final_key={result.final_key}")
    print(f"wrote_final={result.wrote_final}")


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
