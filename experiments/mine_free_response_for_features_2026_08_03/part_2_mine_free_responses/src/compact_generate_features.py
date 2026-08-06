"""Collapse Stage-1 per-batch runner JSONs into batches.jsonl, then delete them.

Discovers timestamped run dirs under
``outputs/generated_features/<group>/outputs/<ts>/``, writes ``batches.jsonl``
(one JSON object per line, sorted by source filename), and removes matching
``NNNNN_*.json`` files. Leaves ``metadata.json`` intact.

Run from root: PYTHONPATH=. uv run python \\
  experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/compact_generate_features.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPERIMENT_PART2_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEATURES_ROOT = EXPERIMENT_PART2_ROOT / "outputs" / "generated_features"
PER_ITEM_JSON_RE = re.compile(r"^\d{5}_.+\.json$")
BATCHES_FILENAME = "batches.jsonl"


def is_per_batch_result(path: Path) -> bool:
    """Return True when ``path`` looks like a runner per-batch result file.

    Parameters
    ----------
    path
        Candidate filesystem path.

    Returns
    -------
    bool
        True when the path is a file whose name matches ``NNNNN_*.json``.
    """
    return path.is_file() and PER_ITEM_JSON_RE.match(path.name) is not None


def discover_run_dirs(features_root: Path) -> list[Path]:
    """Find Stage-1 run dirs that still contain per-batch result JSONs.

    Parameters
    ----------
    features_root
        ``outputs/generated_features`` directory
        (``generated_features/<group>/outputs/<ts>/``).

    Returns
    -------
    list[Path]
        Sorted run directories that contain at least one ``NNNNN_*.json``.

    Raises
    ------
    FileNotFoundError
        When ``features_root`` does not exist.
    """
    if not features_root.is_dir():
        raise FileNotFoundError(f"Features root not found: {features_root}")

    run_dirs: list[Path] = []
    for group_dir in sorted(features_root.iterdir()):
        runs_parent = group_dir / "outputs"
        if not runs_parent.is_dir():
            continue
        for run_dir in sorted(runs_parent.iterdir()):
            if not run_dir.is_dir():
                continue
            if any(is_per_batch_result(p) for p in run_dir.iterdir()):
                run_dirs.append(run_dir)
    return run_dirs


def compact_run_dir(run_dir: Path, *, dry_run: bool = False) -> tuple[Path, int]:
    """Write ``batches.jsonl`` from per-batch JSONs, then delete those JSONs.

    Parameters
    ----------
    run_dir
        Timestamped Stage-1 runner folder.
    dry_run
        When True, print planned actions without writing or deleting.

    Returns
    -------
    tuple[Path, int]
        Path to ``batches.jsonl`` and number of batches compacted.

    Raises
    ------
    ValueError
        When no per-batch result files are found.
    """
    batch_paths = sorted(p for p in run_dir.iterdir() if is_per_batch_result(p))
    if not batch_paths:
        raise ValueError(f"No per-batch result JSON files under {run_dir}")

    out_path = run_dir / BATCHES_FILENAME
    if dry_run:
        print(
            f"[dry-run] {run_dir}: would write {out_path.name} "
            f"({len(batch_paths)} rows) and delete {len(batch_paths)} JSON files"
        )
        return out_path, len(batch_paths)

    with out_path.open("w", encoding="utf-8") as handle:
        for path in batch_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    for path in batch_paths:
        path.unlink()

    print(
        f"{run_dir}: wrote {out_path.name} ({len(batch_paths)} rows), "
        f"deleted {len(batch_paths)} JSON files"
    )
    return out_path, len(batch_paths)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage-1 compaction.

    Parameters
    ----------
    argv
        Optional argument list. When None, uses ``sys.argv``.

    Returns
    -------
    argparse.Namespace
        Parsed CLI flags.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Collapse NNNNN_*.json Stage-1 runner outputs into batches.jsonl "
            "and delete the per-batch files."
        )
    )
    parser.add_argument(
        "--features-root",
        type=Path,
        default=DEFAULT_FEATURES_ROOT,
        help=f"Stage-1 features root (default: {DEFAULT_FEATURES_ROOT}).",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=None,
        help=(
            "Optional specific run dir to compact. "
            "May be repeated. Default: discover all under --features-root."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing or deleting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: compact discovered or explicit Stage-1 run dirs.

    Parameters
    ----------
    argv
        Optional argument list. When None, uses ``sys.argv``.
    """
    args = parse_args(argv)
    run_dirs = args.run_dir if args.run_dir else discover_run_dirs(args.features_root)
    if not run_dirs:
        print(f"No run dirs with per-batch JSONs under {args.features_root}")
        return

    total = 0
    for run_dir in run_dirs:
        _, n = compact_run_dir(run_dir, dry_run=args.dry_run)
        total += n
    print(f"Done: {len(run_dirs)} run dir(s), {total} batch(es)")


if __name__ == "__main__":
    main()
