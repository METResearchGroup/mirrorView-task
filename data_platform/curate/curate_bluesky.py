"""Curate Bluesky posts: join labels, apply business rules, export CSV.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \\
        --dataset-id bluesky_<uuid> --config mirrorview.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.curate.runner import CuratePlatformSpec, curate_with_spec, make_curate_cli
from data_platform.utils.platform_specific_columns import BLUESKY_COLUMNS
from data_platform.utils.storage import BlueskyStorageManager

CONFIGS_DIR = Path(__file__).resolve().parent / "configs" / "bluesky"

app = typer.Typer(add_completion=False)

BLUESKY_CURATE_SPEC = CuratePlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    columns=BLUESKY_COLUMNS,
    record_noun="posts",
    require_features_complete=True,
    require_all_runs_complete=True,
    skip_if_up_to_date=True,
)


def curate(config_path: Path, dataset_id: str) -> Path:
    return curate_with_spec(config_path, dataset_id, BLUESKY_CURATE_SPEC)


main = make_curate_cli(
    BLUESKY_CURATE_SPEC,
    CONFIGS_DIR,
    configs_help="Curate config under data_platform/curate/configs/bluesky/",
)

app.command()(main)


if __name__ == "__main__":
    app()
