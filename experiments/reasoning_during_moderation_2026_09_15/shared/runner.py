"""Run thinking-mode completions for the reasoning-during-moderation experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations


def generation_seed(post_id: str) -> int:
    raise NotImplementedError
