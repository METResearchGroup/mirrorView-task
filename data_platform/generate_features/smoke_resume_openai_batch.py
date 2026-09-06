"""Temporary live smoke for OpenAI Batch partial success and interrupt-and-resume.

Delete this file before merge. Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode partial-success --feature is_news_or_opinion --post-count 3

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode interrupt --feature is_news_or_opinion --post-count 5 --stop-after-submit

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode resume --feature is_news_or_opinion --run-dir /tmp/<printed-run-dir>
"""

from __future__ import annotations

from pathlib import Path

import typer


def main(
    mode: str = typer.Option(..., "--mode"),
    feature: str = typer.Option("is_news_or_opinion", "--feature"),
    post_count: int = typer.Option(3, "--post-count"),
    stop_after_submit: bool = typer.Option(False, "--stop-after-submit"),
    run_dir: Path | None = typer.Option(None, "--run-dir"),
) -> None:
    """Run one smoke mode: partial-success, interrupt, or resume."""
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
