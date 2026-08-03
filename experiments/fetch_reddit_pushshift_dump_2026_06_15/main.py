"""Backward-compatible CLI entrypoint for experiment orchestration."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.main import app


if __name__ == "__main__":
    app()
