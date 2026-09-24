"""CLI for discovery LLM feature generation (mixed and single-class).

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \\
      --arm original_only \\
      --batch-design mixed \\
      --smoke \\
      --seed 42
"""

from __future__ import annotations


def main() -> None:
    """Parse CLI args and run smoke or production discovery generation."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
