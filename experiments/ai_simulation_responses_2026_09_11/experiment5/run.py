"""Experiment 5 error-analysis CLI wrapper."""

from __future__ import annotations

import argparse

from experiments.ai_simulation_responses_2026_09_11.shared.run import main as shared_main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse experiment 5 flags."""
    parser = argparse.ArgumentParser(description="Experiment 5 error analysis")
    parser.add_argument("--analyze-errors", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Dispatch experiment 5 commands."""
    args = parse_args(argv)
    if args.analyze_errors:
        shared_main(["--analyze-errors"])
        return
    raise SystemExit("No command selected")


if __name__ == "__main__":
    main()
