"""Write a dollar estimate for the OpenAI-sized Bedrock runs from smoke metrics.

Run from the repository root:

    PYTHONPATH=. uv run python \\
        experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, REPO_ROOT

SIZE_POST_COUNTS = (100, 200, 300, 400, 500, 1000, 2000, 5000)
PROCESS_COUNTS = (2, 4, 6, 8)
POSTS_PER_PROCESS = 2000
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
TOKENS_PER_MILLION = 1_000_000
CEILING_MULTIPLIER = 2
EXPERIMENT_DIR = REPO_ROOT / "experiments" / "bedrock_batch_parallelization_2026_09_06"
SMOKE_METRICS_PATH = EXPERIMENT_DIR / "smoke_metrics.json"
COST_ESTIMATE_PATH = EXPERIMENT_DIR / "COST_ESTIMATE.md"
WROTE_PREFIX = "Wrote "


def estimated_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate on-demand Nova Micro cost from Ohio token rates."""
    input_cost = input_tokens * ON_DEMAND_INPUT_USD_PER_MILLION
    output_cost = output_tokens * ON_DEMAND_OUTPUT_USD_PER_MILLION
    return (input_cost + output_cost) / TOKENS_PER_MILLION


def tokens_for_posts(
    post_count: int,
    mean_input: float,
    mean_output: float,
) -> tuple[int, int]:
    """Return rounded input and output token totals for a post count."""
    return (
        round(mean_input * post_count),
        round(mean_output * post_count),
    )


def load_smoke_metrics(path: Path) -> dict:
    """Load smoke_metrics.json written by the 100-post Bedrock smoke."""
    return json.loads(path.read_text(encoding="utf-8"))


def render_cost_estimate(metrics: dict) -> str:
    """Return COST_ESTIMATE.md text scaled from the smoke means."""
    mean_input = float(metrics["estimated_input_tokens_per_request"])
    mean_output = float(metrics["estimated_output_tokens_per_request"])
    size_posts = sum(SIZE_POST_COUNTS)
    process_posts = sum(PROCESS_COUNTS) * POSTS_PER_PROCESS
    size_input, size_output = tokens_for_posts(size_posts, mean_input, mean_output)
    process_input, process_output = tokens_for_posts(
        process_posts, mean_input, mean_output
    )
    size_usd = estimated_cost_usd(size_input, size_output)
    process_usd = estimated_cost_usd(process_input, process_output)
    combined_usd = size_usd + process_usd
    ceiling_usd = combined_usd * CEILING_MULTIPLIER
    smoke_usd = float(metrics["estimated_cost_usd"])
    return (
        "# Bedrock Nova Micro cost estimate\n\n"
        f"Model: `{DEFAULT_BEDROCK_NOVA_MICRO}`\n\n"
        "On-demand Ohio rates: "
        f"${ON_DEMAND_INPUT_USD_PER_MILLION} per million input tokens, "
        f"and ${ON_DEMAND_OUTPUT_USD_PER_MILLION} per million output tokens.\n\n"
        "Mean tokens per request from the 100-post smoke: "
        f"{mean_input:.2f} input, and {mean_output:.2f} output.\n\n"
        f"100-post smoke actual cost: ${smoke_usd:.4f}\n\n"
        f"Size runs totaling {size_posts:,} posts: ${size_usd:.4f} "
        f"({size_input:,} input tokens, {size_output:,} output tokens).\n\n"
        f"Process-count runs totaling {process_posts:,} posts: ${process_usd:.4f} "
        f"({process_input:,} input tokens, {process_output:,} output tokens).\n\n"
        f"Combined estimate: ${combined_usd:.4f}\n\n"
        f"2x ceiling: ${ceiling_usd:.4f}\n\n"
        "Steps 4 and 5 live jobs wait for operator approval.\n\n"
        "After approval, start the size runs with:\n\n"
        "```bash\n"
        "export AWS_ACCESS_KEY_ID=\"$LAB_AWS_ACCESS_KEY_ID\"\n"
        "export AWS_SECRET_ACCESS_KEY=\"$LAB_AWS_ACCESS_KEY_SECRET\"\n"
        "PYTHONPATH=. uv run python "
        "experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py "
        "--i-approve-the-cost-estimate\n"
        "```\n\n"
        "After approval, start the process-count runs with:\n\n"
        "```bash\n"
        "export AWS_ACCESS_KEY_ID=\"$LAB_AWS_ACCESS_KEY_ID\"\n"
        "export AWS_SECRET_ACCESS_KEY=\"$LAB_AWS_ACCESS_KEY_SECRET\"\n"
        "PYTHONPATH=. uv run python "
        "experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py "
        "--i-approve-the-cost-estimate\n"
        "```\n"
    )


def main() -> None:
    """Write COST_ESTIMATE.md from smoke_metrics.json."""
    metrics = load_smoke_metrics(SMOKE_METRICS_PATH)
    COST_ESTIMATE_PATH.write_text(render_cost_estimate(metrics), encoding="utf-8")
    print(f"{WROTE_PREFIX}{COST_ESTIMATE_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
