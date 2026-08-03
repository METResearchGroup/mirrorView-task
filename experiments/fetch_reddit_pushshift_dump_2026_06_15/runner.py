"""Backward-compatible CLI entrypoint for single-file scoring."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.runner import app


if __name__ == "__main__":
    app()
