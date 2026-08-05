"""One-off: collapse per-item runner JSONs into predictions.jsonl, then delete them.

Discovers timestamped run dirs under ``outputs/<arm>/outputs/<ts>/``, writes
``predictions.jsonl`` (one JSON object per line, sorted by source filename),
and removes matching ``NNNNN_*.json`` files. Leaves ``metadata.json`` intact.

Run from repo root::

    PYTHONPATH=. uv run python \\
      experiments/llm_prompt_engineering_2026_08_05/consolidate_predictions.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUTS_ROOT = EXPERIMENT_ROOT / "outputs"
PER_ITEM_JSON_RE = re.compile(r"^\d{5}_.+\.json$")
PREDICTIONS_FILENAME = "predictions.jsonl"


def is_per_item_prediction(path: Path) -> bool:
    """Return True when ``path`` looks like a runner per-item prediction file."""
    return path.is_file() and PER_ITEM_JSON_RE.match(path.name) is not None


def discover_run_dirs(outputs_root: Path) -> list[Path]:
    """Find timestamped run dirs that still contain per-item prediction JSONs.

    Parameters
    ----------
    outputs_root
        Experiment ``outputs/`` directory (``outputs/<arm>/outputs/<ts>/``).

    Returns
    -------
    list[Path]
        Sorted run directories that contain at least one ``NNNNN_*.json``.
    """
    if not outputs_root.is_dir():
        raise FileNotFoundError(f"Outputs root not found: {outputs_root}")

    run_dirs: list[Path] = []
    for arm_dir in sorted(outputs_root.iterdir()):
        runs_parent = arm_dir / "outputs"
        if not runs_parent.is_dir():
            continue
        for run_dir in sorted(runs_parent.iterdir()):
            if not run_dir.is_dir():
                continue
            if any(is_per_item_prediction(p) for p in run_dir.iterdir()):
                run_dirs.append(run_dir)
    return run_dirs


def consolidate_run_dir(run_dir: Path, *, dry_run: bool = False) -> tuple[Path, int]:
    """Write ``predictions.jsonl`` from per-item JSONs, then delete those JSONs.

    Parameters
    ----------
    run_dir
        Timestamped runner folder.
    dry_run
        When True, print planned actions without writing or deleting.

    Returns
    -------
    tuple[Path, int]
        Path to ``predictions.jsonl`` and number of predictions consolidated.

    Raises
    ------
    ValueError
        When no per-item prediction files are found.
    """
    pred_paths = sorted(p for p in run_dir.iterdir() if is_per_item_prediction(p))
    if not pred_paths:
        raise ValueError(f"No per-item prediction JSON files under {run_dir}")

    out_path = run_dir / PREDICTIONS_FILENAME
    if dry_run:
        print(
            f"[dry-run] {run_dir}: would write {out_path.name} "
            f"({len(pred_paths)} rows) and delete {len(pred_paths)} JSON files"
        )
        return out_path, len(pred_paths)

    with out_path.open("w", encoding="utf-8") as handle:
        for path in pred_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    for path in pred_paths:
        path.unlink()

    print(f"{run_dir}: wrote {out_path.name} ({len(pred_paths)} rows), deleted {len(pred_paths)} JSON files")
    return out_path, len(pred_paths)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Collapse NNNNN_*.json runner outputs into predictions.jsonl "
            "and delete the per-item files."
        )
    )
    parser.add_argument(
        "--outputs-root",
        type=Path,
        default=DEFAULT_OUTPUTS_ROOT,
        help=f"Experiment outputs root (default: {DEFAULT_OUTPUTS_ROOT}).",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=None,
        help=(
            "Optional specific run dir to consolidate. "
            "May be repeated. Default: discover all under --outputs-root."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing or deleting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: consolidate discovered (or explicit) run dirs."""
    args = parse_args(argv)
    run_dirs = args.run_dir if args.run_dir else discover_run_dirs(args.outputs_root)
    if not run_dirs:
        print(f"No run dirs with per-item JSONs under {args.outputs_root}")
        return

    total = 0
    for run_dir in run_dirs:
        _, n = consolidate_run_dir(run_dir, dry_run=args.dry_run)
        total += n
    print(f"Done: {len(run_dirs)} run dir(s), {total} prediction(s)")


if __name__ == "__main__":
    main()
