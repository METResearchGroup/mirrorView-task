"""End-to-end smoke: 1 keep + 1 remove → stage1 + stage2 via the real CLI.

Cheapest live check of the research_tools runner path. Requires OPENAI_API_KEY
in the repo-root `.env`.

Usage:
  PYTHONPATH=. uv run python \\
    experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
"""

from __future__ import annotations

from experiments.llm_based_feature_generation_2026_07_31.main import main

# Tiny fraction still yields >=1 row per class (ceil). Batch size 1+1 → one
# stage-1 item and one stage-2 item.
SMOKE_ARGV = [
    "--sample-fraction",
    "1e-6",
    "--keep-per-batch",
    "1",
    "--remove-per-batch",
    "1",
    "--seed",
    "42",
]


if __name__ == "__main__":
    print("smoke: invoking main with", " ".join(SMOKE_ARGV))
    main(SMOKE_ARGV)
    print("smoke: ok")
