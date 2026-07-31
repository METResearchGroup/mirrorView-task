"""CLI entry point for the LLM feature-generation and theme-synthesis experiment."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from experiments.llm_based_feature_generation_2026_07_31.batching import (
    form_batches,
    load_posts,
    sample_posts,
)
from experiments.llm_based_feature_generation_2026_07_31.stage1 import DEFAULT_MODEL, run_stage1
from experiments.llm_based_feature_generation_2026_07_31.stage2 import run_stage2

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
_METADATA_FILENAME = "metadata.json"


def _load_exclude_ids(path: str | pathlib.Path) -> set[str]:
    """Load message ids to exclude from a metadata file or JSON id list."""
    file_path = pathlib.Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"exclude-ids source not found: {file_path}")

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {str(message_id) for message_id in payload}

    if isinstance(payload, dict):
        run_metadata = payload.get("run_metadata", {})
        message_ids = run_metadata.get("message_ids")
        if isinstance(message_ids, list):
            return {str(message_id) for message_id in message_ids}

    raise ValueError(
        f"Could not parse message ids from {file_path}. "
        "Expected a JSON list or metadata.json with run_metadata.message_ids."
    )


def _assert_unique_batch_ids(batches: list[dict[str, Any]]) -> None:
    """Ensure each message_id appears in at most one batch."""
    seen: set[str] = set()
    for batch in batches:
        for message_id in batch["message_ids"]:
            if message_id in seen:
                raise ValueError(f"Duplicate message_id across batches: {message_id}")
            seen.add(message_id)


def run_pipeline(
    *,
    sample_fraction: float,
    seed: int,
    keep_per_batch: int,
    remove_per_batch: int,
    model: str,
    exclude_ids_from: str | None,
    stage1_only: bool,
    stage2_only: bool,
    stage1_dir: str | None,
) -> dict[str, pathlib.Path | int]:
    """Run stage 1, stage 2, or both and return output paths."""
    if stage2_only and not stage1_dir:
        raise ValueError("--stage2-only requires --stage1-dir")

    stage1_output: pathlib.Path | None = pathlib.Path(stage1_dir) if stage1_dir else None
    stage2_output: pathlib.Path | None = None
    batch_count = 0

    if not stage2_only:
        posts = load_posts()
        exclude_ids = _load_exclude_ids(exclude_ids_from) if exclude_ids_from else None
        sampled = sample_posts(
            posts,
            fraction=sample_fraction,
            seed=seed,
            exclude_ids=exclude_ids,
        )
        batches, leftover = form_batches(
            sampled,
            keep_per_batch=keep_per_batch,
            remove_per_batch=remove_per_batch,
        )
        _assert_unique_batch_ids(batches)
        batch_count = len(batches)
        print(
            f"corpus={len(posts)} sample={len(sampled)} batches={batch_count} "
            f"leftover={len(leftover)}"
        )
        stage1_output = run_stage1(
            batches,
            model=model,
            seed=seed,
            sample_fraction=sample_fraction,
        )
        print(f"stage1_dir={stage1_output}")

    if stage1_only:
        if stage1_output is None:
            raise RuntimeError("stage1 output path missing after stage 1 run")
        return {"stage1_dir": stage1_output, "batch_count": batch_count}

    if stage1_output is None:
        raise RuntimeError("stage1 output path missing before stage 2 run")

    stage2_output = run_stage2(stage1_output, model=model)
    print(f"stage2_dir={stage2_output}")

    theme_count = _count_themes(stage2_output)
    print(f"n_themes={theme_count}")
    return {
        "stage1_dir": stage1_output,
        "stage2_dir": stage2_output,
        "batch_count": batch_count,
        "n_themes": theme_count,
    }


def _count_themes(stage2_dir: pathlib.Path) -> int:
    """Count themes in the first stage-2 result file."""
    for path in sorted(stage2_dir.glob("*.json")):
        if path.name == _METADATA_FILENAME:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        themes = payload.get("result", {}).get("themes", [])
        return len(themes)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the experiment CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run LLM feature generation and theme synthesis on Study Phase 2 Part 2 posts.",
    )
    parser.add_argument("--sample-fraction", type=float, default=0.50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep-per-batch", type=int, default=10)
    parser.add_argument("--remove-per-batch", type=int, default=10)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--exclude-ids-from", type=str, default=None)
    parser.add_argument("--stage1-only", action="store_true")
    parser.add_argument("--stage2-only", action="store_true")
    parser.add_argument("--stage1-dir", type=str, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and run the experiment pipeline."""
    args = build_parser().parse_args(argv)
    if args.stage1_only and args.stage2_only:
        print("Cannot combine --stage1-only and --stage2-only", file=sys.stderr)
        return 2

    run_pipeline(
        sample_fraction=args.sample_fraction,
        seed=args.seed,
        keep_per_batch=args.keep_per_batch,
        remove_per_batch=args.remove_per_batch,
        model=args.model,
        exclude_ids_from=args.exclude_ids_from,
        stage1_only=args.stage1_only,
        stage2_only=args.stage2_only,
        stage1_dir=args.stage1_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
