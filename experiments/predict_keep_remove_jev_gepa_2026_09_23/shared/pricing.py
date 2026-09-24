"""Jev API cost estimation for predict keep/remove experiment.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_pricing.py -q
"""

from __future__ import annotations

JEV_USD_PER_MILLION_INPUT_TOKENS = 0.042
JEV_USD_PER_MILLION_OUTPUT_TOKENS = 0.0


def estimate_jev_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token usage at pinned Jev rates.

    Parameters
    ----------
    input_tokens
        Input token count from the SDK usage block.
    output_tokens
        Output token count from the SDK usage block.

    Returns
    -------
    float
        Estimated cost in USD.
    """
    input_cost = input_tokens * JEV_USD_PER_MILLION_INPUT_TOKENS / 1_000_000
    output_cost = output_tokens * JEV_USD_PER_MILLION_OUTPUT_TOKENS / 1_000_000
    return input_cost + output_cost
