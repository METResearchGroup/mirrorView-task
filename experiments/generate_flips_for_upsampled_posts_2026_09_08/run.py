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
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.generate_flips_for_upsampled_posts_2026_09_08.load_unified_dataset import (
    load_unified_dataset,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    DEFAULT_CACHE_DIR,
    EXPERIMENT_DIR,
    INPUT_ROW_COUNT,
    INPUT_S3_BUCKET,
    INPUT_S3_URI,
    INPUT_SHA256,
    NAMED_SIBLING_S3_KEY,
    NamedFlipCopyResult,
    OUTPUT_S3_BUCKET,
    POST_COLUMNS,
    RESULTS_FILENAME,
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


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    run_id: str = typer.Option(
        "",
        "--run-id",
        help=f"S3 run folder name. The 10-post test uses {SMOKE_RUN_ID}.",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        help=f"Limit rows after load. The 10-post test uses {SMOKE_MAX_POSTS}.",
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
    _maybe_copy_named_sibling(result, max_posts, bucket)


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
    FileNotFoundError
        When the concatenated flips object is missing.
    """
    stored = store.get(result.final_key)
    if stored is None:
        raise FileNotFoundError(result.final_key)
    store.put_new(NAMED_SIBLING_S3_KEY, stored.body)
    return NamedFlipCopyResult(
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, NAMED_SIBLING_S3_KEY),
        sha256=sha256_hex(stored.body),
    )


def _maybe_copy_named_sibling(
    result: FlipRunResult, max_posts: int | None, bucket: str
) -> None:
    if max_posts is not None or not result.wrote_final:
        return
    named = copy_named_sibling_flips(result, CampaignObjectStore(bucket))
    print(f"named_s3_uri={named.s3_uri}")
    print(f"named_sha256={named.sha256}")
    _write_results_md(result, named)


def _write_results_md(result: FlipRunResult, named: NamedFlipCopyResult) -> None:
    path = EXPERIMENT_DIR / RESULTS_FILENAME
    path.write_text(_results_markdown(result, named))


def _results_markdown(result: FlipRunResult, named: NamedFlipCopyResult) -> str:
    return "\n".join(
        [
            *_results_commands(result),
            *_results_counts(result),
            *_results_outputs(result, named),
        ]
    )


def _results_commands(result: FlipRunResult) -> list[str]:
    return [
        "# Generate flips for upsampled posts, results",
        "",
        "## Smoke",
        "",
        "```bash",
        _smoke_command(),
        "```",
        "",
        "## Full run",
        "",
        "```bash",
        _full_run_command(result),
        "```",
        "",
        "## Pinned input",
        "",
        (
            f"Object `{INPUT_S3_URI}` SHA-256 `{INPUT_SHA256}` "
            f"has {INPUT_ROW_COUNT} rows."
        ),
        "",
    ]


def _results_counts(result: FlipRunResult) -> list[str]:
    return [
        "## Counts",
        "",
        "| Field | Value |",
        "| ----- | ----: |",
        f"| `part_count` | {result.part_count} |",
        f"| `row_count` | {result.row_count} |",
        f"| `failed_count` | {result.failed_count} |",
        "",
        f"`row_count` plus `failed_count` is {result.row_count + result.failed_count}.",
        "",
    ]


def _results_outputs(result: FlipRunResult, named: NamedFlipCopyResult) -> list[str]:
    return [
        "## Output",
        "",
        "| File | URI | SHA-256 |",
        "| ---- | --- | ------- |",
        f"| Run-prefix flips | `s3://{OUTPUT_S3_BUCKET}/{result.final_key}` | |",
        f"| Named sibling | `{named.s3_uri}` | `{named.sha256}` |",
        "",
    ]


def _smoke_command() -> str:
    return """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id smoke --max-posts 10"""


def _full_run_command(result: FlipRunResult) -> str:
    run_id = result.run_prefix.rstrip("/").split("/")[-1]
    return f"""export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --run-id {run_id}"""


if __name__ == "__main__":
    sys.exit(app())
