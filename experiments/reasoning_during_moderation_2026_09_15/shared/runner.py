"""Run thinking-mode completions for the reasoning-during-moderation experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import hashlib

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GENERATION_SEED_BYTES,
    UINT32_MODULUS,
)


def generation_seed(post_id: str) -> int:
    """Return a stable 32-bit seed from a post id."""
    digest = hashlib.sha256(f"gen:{post_id}".encode()).digest()
    return int.from_bytes(digest[:GENERATION_SEED_BYTES], "big") % UINT32_MODULUS
