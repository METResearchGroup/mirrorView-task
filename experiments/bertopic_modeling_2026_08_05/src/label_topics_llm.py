"""Stage 3: post-hoc LLM topic labels via bertopic.representation.OpenAI.

Implemented in Step 4 of the experiment plan.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \\
      --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
"""

from __future__ import annotations


def run_label_topics_llm() -> None:
    """Label non-noise topics with gpt-5.4-nano."""
    raise NotImplementedError("Implemented in Step 4")


def main() -> None:
    """CLI entrypoint."""
    run_label_topics_llm()


if __name__ == "__main__":
    main()
