"""Download, extract, stage, and inventory Bolun's Reddit Pushshift package.

Bolun's package is a single tar.zst (~16GB) containing pre-filtered Parquet and
raw Pushshift JSONL.zst files for six political subreddits. The toxicity pipeline
consumes comment JSONL files (RC_*.zst); this script stages them under
data/raw/bolun/comments/ for main.py discovery.

Example:

PYTHONPATH=. uv run python \\
  experiments/fetch_reddit_pushshift_dump_2026_06_15/scripts/prepare_bolun_package.py \\
  --download --extract --stage --inventory
"""

from __future__ import annotations

import io
import json
import shutil
import tarfile
from dataclasses import asdict
from pathlib import Path

import typer
import zstandard as zstd
from tabulate import tabulate

from experiments.fetch_reddit_pushshift_dump_2026_06_15.bolun_ingest import (
    InventoryRow,
    infer_kind,
    infer_month,
)

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    BOLUN_DATA_DIR,
    BOLUN_DRIVE_FILE_ID,
    BOLUN_EXTRACTED_DIR,
    BOLUN_INVENTORY_PATH,
    BOLUN_STAGED_DIR,
    BOLUN_TARBALL,
)

app = typer.Typer(add_completion=False)

EXTRACT_MARKER = BOLUN_EXTRACTED_DIR / ".extract_complete"
ZSTD_WINDOW = 2**31


def _ensure_dirs() -> None:
    BOLUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    BOLUN_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


def _count_zst_jsonl_lines(path: Path) -> int:
    dctx = zstd.ZstdDecompressor(max_window_size=ZSTD_WINDOW)
    count = 0
    with path.open("rb") as fh:
        with dctx.stream_reader(fh) as compressed_reader:
            for line in io.TextIOWrapper(compressed_reader, encoding="utf-8"):
                if line.strip():
                    count += 1
    return count


def _count_parquet_rows(path: Path) -> int:
    import pyarrow.parquet as pq

    return pq.ParquetFile(path).metadata.num_rows


def _count_rows(path: Path, kind: str) -> int | None:
    if kind == "comment_zst" or kind == "submission_zst":
        return _count_zst_jsonl_lines(path)
    if kind in {"comment_parquet", "submission_parquet", "parquet_other"}:
        return _count_parquet_rows(path)
    return None


def download_tarball(*, force: bool = False) -> Path:
    _ensure_dirs()
    if BOLUN_TARBALL.is_file() and not force:
        print(f"Tarball already exists: {BOLUN_TARBALL}")
        return BOLUN_TARBALL

    try:
        import gdown
    except ImportError as exc:
        raise typer.Exit(
            "gdown is required for --download. Run `uv sync --group dev` or pass "
            f"--tarball /path/to/bolun_package.tar.zst after manual download."
        ) from exc

    url = f"https://drive.google.com/uc?id={BOLUN_DRIVE_FILE_ID}"
    print(f"Downloading Bolun package from Google Drive to {BOLUN_TARBALL} ...")
    gdown.download(url, str(BOLUN_TARBALL), quiet=False, fuzzy=True)
    if not BOLUN_TARBALL.is_file():
        raise typer.Exit(f"Download failed; expected {BOLUN_TARBALL}")
    print(f"Downloaded {BOLUN_TARBALL} ({BOLUN_TARBALL.stat().st_size / 1e9:.2f} GB)")
    return BOLUN_TARBALL


def extract_tarball(tarball: Path, *, force: bool = False) -> Path:
    _ensure_dirs()
    if EXTRACT_MARKER.is_file() and not force:
        print(f"Extract already complete: {BOLUN_EXTRACTED_DIR}")
        return BOLUN_EXTRACTED_DIR

    if not tarball.is_file():
        raise typer.Exit(f"Tarball not found: {tarball}")

    if force and BOLUN_EXTRACTED_DIR.exists():
        shutil.rmtree(BOLUN_EXTRACTED_DIR)
        BOLUN_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {tarball} -> {BOLUN_EXTRACTED_DIR} (streaming, may take a while) ...")
    dctx = zstd.ZstdDecompressor(max_window_size=ZSTD_WINDOW)
    with tarball.open("rb") as fh:
        with dctx.stream_reader(fh) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                archive.extractall(path=BOLUN_EXTRACTED_DIR, filter="data")

    EXTRACT_MARKER.write_text(json.dumps({"tarball": str(tarball.resolve())}) + "\n")
    print(f"Extract complete: {BOLUN_EXTRACTED_DIR}")
    return BOLUN_EXTRACTED_DIR


def _discover_data_files(root: Path) -> list[Path]:
    patterns = ("**/RC_*.zst", "**/RS_*.zst", "**/*.parquet")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.glob(pattern))
    return sorted(set(files))


def build_inventory(
    root: Path,
    *,
    count_rows: bool = True,
    use_cache: bool = True,
) -> list[InventoryRow]:
    if use_cache and BOLUN_INVENTORY_PATH.is_file():
        cached = json.loads(BOLUN_INVENTORY_PATH.read_text())
        return [InventoryRow(**row) for row in cached]

    rows: list[InventoryRow] = []
    for path in _discover_data_files(root):
        kind = infer_kind(path)
        month = infer_month(path)
        size_mb = path.stat().st_size / (1024 * 1024)
        row_count: int | None = None
        if count_rows:
            print(f"Counting rows: {path.relative_to(root)} ...")
            try:
                row_count = _count_rows(path, kind)
            except Exception as exc:
                print(f"  warning: could not count rows for {path.name}: {exc}")
        rows.append(
            InventoryRow(
                kind=kind,
                month=month,
                size_mb=round(size_mb, 2),
                rows=row_count,
                path=str(path.relative_to(root)),
            )
        )

    BOLUN_INVENTORY_PATH.write_text(
        json.dumps([asdict(row) for row in rows], indent=2) + "\n"
    )
    return rows


def print_inventory_table(rows: list[InventoryRow]) -> None:
    table_rows = [
        [
            row.kind,
            row.month or "",
            f"{row.size_mb:.2f}",
            f"{row.rows:,}" if row.rows is not None else "—",
            row.path,
        ]
        for row in rows
    ]
    print(
        tabulate(
            table_rows,
            headers=["kind", "month", "size_mb", "rows", "path"],
            tablefmt="simple",
        )
    )

    def _sum_rows(kind_prefix: str) -> int:
        return sum(row.rows or 0 for row in rows if row.kind.startswith(kind_prefix))

    print()
    print(f"Files: {len(rows)}")
    print(f"Total comment_zst rows: { _sum_rows('comment_zst'):,}")
    print(f"Total submission_zst rows: {_sum_rows('submission_zst'):,}")
    print(f"Total comment_parquet rows: {_sum_rows('comment_parquet'):,}")
    print(f"Total submission_parquet rows: {_sum_rows('submission_parquet'):,}")


def stage_comment_zst_files(root: Path, *, force: bool = False) -> list[Path]:
    BOLUN_STAGED_DIR.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for src in sorted(root.glob("**/RC_*.zst")):
        dest = BOLUN_STAGED_DIR / src.name
        if dest.exists() or dest.is_symlink():
            if force:
                dest.unlink()
            else:
                staged.append(dest.resolve())
                continue
        dest.symlink_to(src.resolve())
        staged.append(dest.resolve())
    print(f"Staged {len(staged)} comment files under {BOLUN_STAGED_DIR}")
    return staged


@app.command()
def main(
    tarball: Path | None = typer.Option(
        None,
        "--tarball",
        help="Path to bolun_package.tar.zst (default: data/bolun/bolun_package.tar.zst).",
    ),
    download: bool = typer.Option(False, "--download", help="Download tarball from Google Drive."),
    extract: bool = typer.Option(False, "--extract", help="Extract tarball to data/bolun/extracted/."),
    stage: bool = typer.Option(
        False,
        "--stage",
        help="Symlink RC_*.zst comment files into data/raw/bolun/comments/ for main.py.",
    ),
    inventory: bool = typer.Option(
        False,
        "--inventory",
        help="Build and print file inventory (row counts; caches to inventory.json).",
    ),
    skip_row_counts: bool = typer.Option(
        False,
        "--skip-row-counts",
        help="Inventory file sizes only; skip slow JSONL line counts.",
    ),
    force: bool = typer.Option(False, "--force", help="Re-download, re-extract, or re-stage."),
    all_steps: bool = typer.Option(
        False,
        "--all",
        help="Equivalent to --download --extract --stage --inventory.",
    ),
) -> None:
    """Prepare Bolun's pre-filtered Reddit package for the toxicity pipeline."""

    if all_steps:
        download = extract = stage = inventory = True

    if not any([download, extract, stage, inventory]):
        print("No steps selected. Pass --all or individual flags (--download, --extract, --stage, --inventory).")
        raise typer.Exit(code=1)

    archive = tarball or BOLUN_TARBALL
    if download:
        archive = download_tarball(force=force)

    if extract:
        extract_tarball(archive, force=force)

    if not BOLUN_EXTRACTED_DIR.is_dir():
        raise typer.Exit(
            f"Extracted data not found at {BOLUN_EXTRACTED_DIR}. Run with --extract first."
        )

    if stage:
        stage_comment_zst_files(BOLUN_EXTRACTED_DIR, force=force)

    if inventory:
        inv_rows = build_inventory(
            BOLUN_EXTRACTED_DIR,
            count_rows=not skip_row_counts,
            use_cache=not force,
        )
        print_inventory_table(inv_rows)


if __name__ == "__main__":
    app()
