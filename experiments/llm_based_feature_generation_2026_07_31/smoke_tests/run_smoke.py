"""Tiny live smoke test for the LLM feature-generation experiment."""

from __future__ import annotations

import sys

from experiments.llm_based_feature_generation_2026_07_31.main import run_pipeline


def main() -> int:
    """Run a minimal end-to-end live sample through the real CLI pipeline."""
    argv = [
        "--sample-fraction",
        "1e-6",
        "--keep-per-batch",
        "1",
        "--remove-per-batch",
        "1",
        "--seed",
        "42",
    ]
    print("smoke argv:", " ".join(argv))
    run_pipeline(
        sample_fraction=1e-6,
        seed=42,
        keep_per_batch=1,
        remove_per_batch=1,
        model="gpt-5.4-nano",
        exclude_ids_from=None,
        stage1_only=False,
        stage2_only=False,
        stage1_dir=None,
    )
    print("smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
