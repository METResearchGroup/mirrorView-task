"""Copy leftover flat feature files into a timestamped run directory.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/copy_flat_features.py \\
        --platform bluesky --dataset-id bluesky_<uuid>
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from pydantic import BaseModel

from data_platform.generate_features.platform_cli import feature_run_dir
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.storage import StorageManager, StorageStage

FLAT_FEATURE_SUFFIXES = {".csv", ".json", ".jsonl"}

app = typer.Typer(add_completion=False)


def flat_feature_files(features_root: Path) -> list[Path]:
    """Return leftover files sitting directly under the features stage root."""
    if not features_root.exists():
        return []
    return sorted(
        path
        for path in features_root.iterdir()
        if path.is_file()
        and path.suffix in FLAT_FEATURE_SUFFIXES
        and not path.name.endswith(".tmp")
    )


def copy_flat_features_into_run(features_root: Path, run_dir: Path) -> list[Path]:
    """Copy leftover root-level feature files into ``run_dir``.

    Leaves the originals in place. Raises if a name already exists in the
    destination so a live timestamped run is not overwritten.
    """
    sources = flat_feature_files(features_root)
    if not sources:
        return []
    run_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in sources:
        dest = run_dir / src.name
        if dest.exists():
            raise FileExistsError(f"Refusing to overwrite {dest}")
        shutil.copy2(src, dest)
        copied.append(dest)
    return copied


def copy_flat_features_for_dataset(
    platform: str,
    dataset_id: str,
    *,
    run_dir_name: str | None = None,
) -> Path | None:
    """Copy leftover flat files for one dataset into a timestamped feature run."""
    dataset_id = validate_dataset_id(dataset_id)
    feature_storage = StorageManager(
        platform,
        StorageStage.FEATURES,
        BaseModel,
        dataset_id,
        records_filename="features",
    )
    sources = flat_feature_files(feature_storage.root_dir)
    if not sources:
        return None
    run_dir = feature_run_dir(feature_storage, run_dir_name)
    copy_flat_features_into_run(feature_storage.root_dir, run_dir)
    return run_dir


@app.command()
def main(
    platform: str = typer.Option(..., "--platform", help="bluesky, twitter, or reddit"),
    dataset_id: str = typer.Option(..., "--dataset-id"),
    run_dir: str | None = typer.Option(
        None,
        "--run-dir",
        help="Feature run timestamp to copy into. Omit to create a new folder.",
    ),
) -> None:
    """Copy leftover features/*.csv files into features/{timestamp}/."""
    dest = copy_flat_features_for_dataset(platform, dataset_id, run_dir_name=run_dir)
    if dest is None:
        print(f"copy_flat_features: no leftover files under {platform}/{dataset_id}/features/")
        return
    print(f"copy_flat_features: copied leftover files into {dest}")


if __name__ == "__main__":
    app()
