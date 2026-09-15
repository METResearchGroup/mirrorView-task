"""Run experiment 1 study-prompt completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations


def main() -> None:
    posts = _load_posts()
    _run_completions(posts)


def _load_posts() -> object:
    raise NotImplementedError


def _run_completions(posts: object) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
