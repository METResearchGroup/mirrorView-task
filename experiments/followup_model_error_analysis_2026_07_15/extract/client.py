"""OpenAI ChatOpenAI factory for follow-up feature extraction."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from lib.load_env_vars import EnvVarsContainer

PRIMARY_MODEL = "gpt-5.5"
FALLBACK_MODEL = "gpt-5.4-nano"  # only if primary unavailable


def get_llm(model: str | None = None) -> ChatOpenAI:
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model or PRIMARY_MODEL, temperature=0.0, api_key=api_key)


def resolve_model(prefer_primary: bool = True) -> str:
    """Return primary model; callers may fall back to FALLBACK_MODEL on API errors."""
    return PRIMARY_MODEL if prefer_primary else FALLBACK_MODEL
