"""Stage 1: resolve Titan original-text embeddings into the local cache.

Implemented in Step 2 of the experiment plan.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py
"""

from __future__ import annotations


def run_load_embeddings() -> None:
    """Resolve Titan vectors into ``outputs/embeddings/original/``."""
    raise NotImplementedError("Implemented in Step 2")


def main() -> None:
    """CLI entrypoint."""
    run_load_embeddings()


if __name__ == "__main__":
    main()
