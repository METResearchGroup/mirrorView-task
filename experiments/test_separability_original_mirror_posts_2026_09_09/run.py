"""Run the separability original vs mirror experiment.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and pull request 273 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
then wrote 10000 presentations
and S3 object experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet exists
and gold_human_slot is first or second on every row
and first_text plus second_text are the original and the mirror in some order
and no OpenAI or Bedrock call is made

given the presentation key already exists
when the command is run again
then the process raises FileExistsError
and the catalog S3 object is unchanged

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from data_platform.generate_features.models import CampaignRunConfig
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    CACHE_DIRNAME,
    CAMPAIGN_ID,
    CAMPAIGN_PLATFORM,
    DATASET_ID,
    EngineName,
    EXPERIMENT_DIRNAME,
    OUTPUT_S3_BUCKET,
    PREPROCESSED_RUN,
    campaign_batch_size,
    pinned_catalog,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.loader import (
    build_presentation_table,
    load_catalog,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.write import (
    print_presentation_summary,
    require_presentation_key_absent,
    upload_presentation,
)
from lib.constants import REPO_ROOT

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    write_presentation: bool = typer.Option(
        False, "--write-presentation", help="Write the shared presentation parquet."
    ),
    engine: str | None = typer.Option(
        None, "--engine", help="Labeling engine: openai or bedrock."
    ),
    smoke: bool = typer.Option(False, "--smoke", help="Label only the smoke subset."),
    score: bool = typer.Option(False, "--score", help="Score labels and write RESULTS.md."),
) -> None:
    """Write presentations, label pairs, or score results."""
    _validate_cli_flags(write_presentation, engine, smoke, score)
    if write_presentation:
        _write_presentation()
        return
    if score:
        raise NotImplementedError
    if engine is not None:
        raise NotImplementedError


def _validate_cli_flags(
    write_presentation: bool,
    engine: str | None,
    smoke: bool,
    score: bool,
) -> None:
    """Ensure mutually exclusive CLI modes are not combined.

    Raises
    ------
    ValueError
        When flags are missing, combined, or invalid.
    """
    if smoke and engine is None:
        raise ValueError("--smoke requires --engine")
    selected = [write_presentation, engine is not None, score]
    if sum(selected) != 1:
        raise ValueError("choose exactly one of --write-presentation, --engine, or --score")
    if engine is not None:
        _parse_engine_name(engine)


def _parse_engine_name(engine: str) -> EngineName:
    try:
        return EngineName(engine)
    except ValueError as error:
        raise ValueError(f"unsupported engine: {engine}") from error


def _write_presentation() -> None:
    """Download the catalog, shuffle pairs, and upload presentations.parquet."""
    source = pinned_catalog()
    experiment_dir = _experiment_dir()
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    require_presentation_key_absent(store)
    catalog = load_catalog(source, store, experiment_dir / CACHE_DIRNAME)
    presentations = build_presentation_table(catalog)
    result = upload_presentation(presentations, experiment_dir, store)
    print_presentation_summary(result)


def _experiment_dir() -> Path:
    return REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME


def _campaign_config() -> CampaignRunConfig:
    return CampaignRunConfig(
        campaign_id=CAMPAIGN_ID,
        dataset_id=DATASET_ID,
        preprocessed_run=PREPROCESSED_RUN,
        platform=CAMPAIGN_PLATFORM,
        batch_size=campaign_batch_size(),
    )


if __name__ == "__main__":
    try:
        app()
    except (FileExistsError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
