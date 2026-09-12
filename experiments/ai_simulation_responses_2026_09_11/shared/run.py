"""CLI entrypoint for the AI simulation responses experiment."""

from __future__ import annotations

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse shared runner flags."""
    parser = argparse.ArgumentParser(
        description="AI simulation responses shared runner",
    )
    parser.add_argument("--write-cohort", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--estimate-cost", action="store_true")
    parser.add_argument("--print-experiment-2-prompt", action="store_true")
    parser.add_argument("--experiment", type=int, choices=[1, 2, 3, 4, 5])
    parser.add_argument(
        "--model",
        choices=[
            "openai",
            "bedrock_micro_nova",
            "bedrock_qwen",
            "bedrock_claude",
        ],
    )
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--analyze-errors", action="store_true")
    return parser.parse_args(argv)


def write_cohort_command() -> None:
    """Download September CSVs, confirm cohort, and upload parquet."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """Dispatch shared runner commands."""
    args = parse_args(argv)
    if args.write_cohort:
        write_cohort_command()
        return
    if args.smoke or args.estimate_cost or args.print_experiment_2_prompt:
        raise NotImplementedError
    if args.score or args.analyze_errors or args.experiment is not None:
        raise NotImplementedError
    raise SystemExit("No command selected")


if __name__ == "__main__":
    main()
