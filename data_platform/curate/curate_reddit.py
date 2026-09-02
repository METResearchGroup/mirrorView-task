"""Curate Reddit comments: join labels, apply business rules, export CSV.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/curate/curate_reddit.py \\
        --dataset-id reddit_<uuid> --config mirrorview.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.curate.runner import CuratePlatformSpec, curate_with_spec, make_curate_cli
from data_platform.utils.platform_specific_columns import REDDIT_COLUMNS
from data_platform.utils.storage import RedditStorageManager

CONFIGS_DIR = Path(__file__).resolve().parent / "configs" / "reddit"

app = typer.Typer(add_completion=False)

REDDIT_CURATE_SPEC = CuratePlatformSpec(
    platform="reddit",
    storage_cls=RedditStorageManager,
    columns=REDDIT_COLUMNS,
    record_noun="comments",
)


def curate(config_path: Path, dataset_id: str) -> Path:
    return curate_with_spec(config_path, dataset_id, REDDIT_CURATE_SPEC)


main = make_curate_cli(
    REDDIT_CURATE_SPEC,
    CONFIGS_DIR,
    configs_help="Curate config under data_platform/curate/configs/reddit/",
)

app.command()(main)


if __name__ == "__main__":
    app()
