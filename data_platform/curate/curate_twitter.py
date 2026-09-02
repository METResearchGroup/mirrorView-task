"""Curate Twitter posts: join labels, apply business rules, export CSV.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/curate/curate_twitter.py \\
        --dataset-id twitter_<uuid> --config mirrorview.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.curate.runner import CuratePlatformSpec, curate_with_spec, make_curate_cli
from data_platform.utils.platform_specific_columns import TWITTER_COLUMNS
from data_platform.utils.storage import TwitterStorageManager

CONFIGS_DIR = Path(__file__).resolve().parent / "configs" / "twitter"

app = typer.Typer(add_completion=False)

TWITTER_CURATE_SPEC = CuratePlatformSpec(
    platform="twitter",
    storage_cls=TwitterStorageManager,
    columns=TWITTER_COLUMNS,
    record_noun="posts",
)

ID_COLUMN = TWITTER_COLUMNS.records_id_column
FEATURE_FILE_ID_COLUMN = TWITTER_COLUMNS.feature_file_id_column


def curate(config_path: Path, dataset_id: str) -> str:
    return curate_with_spec(config_path, dataset_id, TWITTER_CURATE_SPEC)


main = make_curate_cli(
    TWITTER_CURATE_SPEC,
    CONFIGS_DIR,
    configs_help="Curate config under data_platform/curate/configs/twitter/",
)

app.command()(main)


if __name__ == "__main__":
    app()
