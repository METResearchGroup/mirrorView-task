"""Token pricing helpers for OpenAI gpt-5.5 / gpt-5.4-nano.

PRICING_AS_OF: 2026-07-15 — rates from https://openai.com/api/pricing
"""

from __future__ import annotations

PRICING_AS_OF = "2026-07-15"

PRICING_USD_PER_1M = {
    "gpt-5.5": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
}

# Pre-run estimate assumptions (spec)
AVG_INPUT_TOKENS = 15_000
AVG_OUTPUT_TOKENS = 6_000


def estimate_call_cost_usd(model: str, usage: dict) -> float:
    rates = PRICING_USD_PER_1M[model]
    prompt = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0)
    cached = usage.get("cached_tokens")
    if cached is None:
        details = usage.get("prompt_tokens_details") or usage.get("input_token_details") or {}
        if isinstance(details, dict):
            cached = details.get("cached_tokens") or details.get("cache_read") or 0
        else:
            cached = getattr(details, "cache_read", 0) or 0
    cached = int(cached or 0)
    completion = int(
        usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
    )
    billable_input = max(prompt - cached, 0)
    return (
        billable_input * rates["input"] / 1_000_000
        + cached * rates["cached_input"] / 1_000_000
        + completion * rates["output"] / 1_000_000
    )


def estimate_budget_usd(n_calls: int, model: str = "gpt-5.5") -> float:
    rates = PRICING_USD_PER_1M[model]
    return (
        n_calls * AVG_INPUT_TOKENS * rates["input"]
        + n_calls * AVG_OUTPUT_TOKENS * rates["output"]
    ) / 1_000_000


def usage_from_langchain_message(raw) -> dict:
    """Normalize LangChain AIMessage usage_metadata into prompt/completion/cached."""
    meta = getattr(raw, "usage_metadata", None) or {}
    if not isinstance(meta, dict):
        meta = dict(meta) if meta else {}
    prompt = int(meta.get("input_tokens", 0) or meta.get("prompt_tokens", 0) or 0)
    completion = int(meta.get("output_tokens", 0) or meta.get("completion_tokens", 0) or 0)
    cached = 0
    details = meta.get("input_token_details") or meta.get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        cached = int(details.get("cache_read", 0) or details.get("cached_tokens", 0) or 0)
    elif details is not None:
        cached = int(getattr(details, "cache_read", 0) or 0)
    resp_meta = getattr(raw, "response_metadata", None) or {}
    token_usage = resp_meta.get("token_usage") or resp_meta.get("usage") or {}
    if not prompt and token_usage:
        prompt = int(token_usage.get("prompt_tokens", 0) or 0)
        completion = int(token_usage.get("completion_tokens", 0) or 0)
        details = token_usage.get("prompt_tokens_details") or {}
        if isinstance(details, dict):
            cached = int(details.get("cached_tokens", 0) or 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cached_tokens": cached,
        "input_tokens": prompt,
        "output_tokens": completion,
    }
