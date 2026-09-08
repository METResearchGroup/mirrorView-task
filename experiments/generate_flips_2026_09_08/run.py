"""Run flip generation on the pinned filtered stimulus sample.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned filtered parquet exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id smoke --max-posts 10
then part_count=1
and row_count + failed_count = 10
and S3 object experiments/generate_flips_2026_09_08/smoke/batches/part-00000.parquet exists
and stdout prints run_prefix=experiments/generate_flips_2026_09_08/smoke/

given the same command is run again
then Bedrock is not called for those 10 ids
and part-00000 is not rewritten

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --help
"""

from __future__ import annotations

import sys

import typer

from data_platform.generate_features.engines.bedrock_engine import (
    create_bedrock_runtime_client,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_flips_2026_09_08.load_filtered_dataset import (
    load_filtered_dataset,
)
from experiments.generate_flips_2026_09_08.sources import (
    OUTPUT_S3_BUCKET,
    POST_COLUMNS,
    RUN_KEY_PREFIX,
    pinned_filtered_source,
)
from lib.constants import DEFAULT_BEDROCK_SONNET_MODEL, REPO_ROOT
from lib.timestamp_utils import get_current_timestamp
from shared.flip_generation.generate_flips import (
    BATCH_SIZE,
    MAX_CONCURRENCY,
    MAX_TOKENS,
    generate_flips,
)

EXPERIMENT_DIR = REPO_ROOT / "experiments" / "generate_flips_2026_09_08"
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    run_id: str | None = typer.Option(None, "--run-id"),
    max_posts: int | None = typer.Option(None, "--max-posts"),
    bucket: str = typer.Option(OUTPUT_S3_BUCKET, "--bucket"),
) -> None:
    """Load the pinned filtered parquet and generate mirrored posts.

    Parameters
    ----------
    run_id
        S3 run folder name. Defaults to the current timestamp when omitted.
    max_posts
        When set, only the first N loaded rows are flipped.
    bucket
        S3 bucket for flip output artifacts.
    """
    resolved_run_id = run_id if run_id is not None else get_current_timestamp()
    run_prefix = f"{RUN_KEY_PREFIX}{resolved_run_id}/"

    source = pinned_filtered_source()
    store = CampaignObjectStore(bucket)
    dataset = load_filtered_dataset(source, store, DEFAULT_CACHE_DIR)
    posts = dataset.loc[:, list(POST_COLUMNS)]
    if max_posts is not None:
        posts = posts.head(max_posts)

    client = create_bedrock_runtime_client()
    result = generate_flips(
        posts,
        store,
        run_prefix,
        client,
        BATCH_SIZE,
        MAX_CONCURRENCY,
        MAX_TOKENS,
        DEFAULT_BEDROCK_SONNET_MODEL,
    )

    print(f"run_prefix={result.run_prefix}")
    print(f"part_count={result.part_count}")
    print(f"row_count={result.row_count}")
    print(f"failed_count={result.failed_count}")
    print(f"final_key={result.final_key}")
    print(f"wrote_final={result.wrote_final}")


if __name__ == "__main__":
    sys.exit(app())
