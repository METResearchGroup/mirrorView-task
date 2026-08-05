"""Stage 2: fit BERTopic on original posts with precomputed Titan embeddings.

Implemented in Step 3 of the experiment plan. No LLM in this stage.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --sample-size 50
"""

from __future__ import annotations


def run_fit_bertopic() -> None:
    """Fit BERTopic and write topics artifacts."""
    raise NotImplementedError("Implemented in Step 3")


def main() -> None:
    """CLI entrypoint."""
    run_fit_bertopic()


if __name__ == "__main__":
    main()
