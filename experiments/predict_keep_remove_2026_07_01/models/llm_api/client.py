"""OpenAI client factory for keep/remove prompting.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from lib.load_env_vars import EnvVarsContainer


def get_llm(*, model_name: str, temperature: float = 0.0) -> ChatOpenAI:
    """Create a LangChain ChatOpenAI client using repo env wiring."""
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        temperature=temperature,
    )

