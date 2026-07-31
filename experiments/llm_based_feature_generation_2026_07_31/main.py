"""CLI entry for the two-stage feature generation → theme synthesis pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.llm_based_feature_generation_2026_07_31.batching import (
    EXPERIMENT_ROOT,
    all_message_ids,
    form_batches,
    load_exclude_ids,
    load_posts,
    sample_posts,
)
from experiments.llm_based_feature_generation_2026_07_31.stage1 import (
    DEFAULT_MODEL,
    run_stage1,
)
from experiments.llm_based_feature_generation_2026_07_31.stage2 import run_stage2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "LLM feature generation then theme synthesis on Study 2 keep/remove posts. "
            "Default sample fraction is 0.01 (pilot). Use 0.50 only after cost gate."
        )
    )
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=0.01,
        help="Fraction of Study 2 posts to sample (default: 0.01 pilot; target: 0.50).",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep-per-batch", type=int, default=10)
    parser.add_argument("--remove-per-batch", type=int, default=10)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument(
        "--exclude-ids-from",
        type=str,
        default=None,
        help=(
            "Path to prior stage-1 metadata.json (with run_metadata.message_ids) "
            "or a JSON list of message ids to exclude before sampling."
        ),
    )
    parser.add_argument(
        "--stage1-only",
        action="store_true",
        help="Run feature generation only.",
    )
    parser.add_argument(
        "--stage2-only",
        action="store_true",
        help="Run theme synthesis only (requires --stage1-dir).",
    )
    parser.add_argument(
        "--stage1-dir",
        type=str,
        default=None,
        help="Existing stage-1 output directory for --stage2-only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.stage1_only and args.stage2_only:
        raise SystemExit("Choose at most one of --stage1-only / --stage2-only.")

    if args.stage2_only:
        if not args.stage1_dir:
            raise SystemExit("--stage2-only requires --stage1-dir.")
        stage2_dir = run_stage2(
            args.stage1_dir,
            output_base_path=EXPERIMENT_ROOT,
            model=args.model,
        )
        print(f"stage2_dir={stage2_dir}")
        _print_theme_summary(stage2_dir)
        return

    exclude_ids = load_exclude_ids(args.exclude_ids_from)
    df = load_posts()
    sample = sample_posts(
        df,
        fraction=args.sample_fraction,
        seed=args.seed,
        exclude_ids=exclude_ids,
    )
    batches, leftover = form_batches(
        sample,
        keep_per_batch=args.keep_per_batch,
        remove_per_batch=args.remove_per_batch,
    )
    message_ids = all_message_ids(batches)
    print(
        f"corpus_posts={len(df)} sample={len(sample)} "
        f"batches={len(batches)} leftover={len(leftover)} "
        f"unique_ids={len(message_ids)} excluded={len(exclude_ids)}"
    )

    stage1_dir = run_stage1(
        batches,
        output_base_path=EXPERIMENT_ROOT,
        model=args.model,
        sample_fraction=args.sample_fraction,
        seed=args.seed,
        leftover_count=len(leftover),
    )
    print(f"stage1_dir={stage1_dir}")

    if args.stage1_only:
        return

    stage2_dir = run_stage2(
        stage1_dir,
        output_base_path=EXPERIMENT_ROOT,
        model=args.model,
    )
    print(f"stage2_dir={stage2_dir}")
    _print_theme_summary(stage2_dir)


def _print_theme_summary(stage2_dir: Path) -> None:
    results = sorted(
        p for p in Path(stage2_dir).glob("*.json") if p.name != "metadata.json"
    )
    if not results:
        print("No stage-2 result files found.")
        return
    payload = json.loads(results[0].read_text(encoding="utf-8"))
    themes = payload.get("result", {}).get("themes", [])
    print(f"n_themes={len(themes)}")
    for theme in themes:
        print(f"- [{theme.get('theme_id')}] {theme.get('theme_label')}")


if __name__ == "__main__":
    main()
