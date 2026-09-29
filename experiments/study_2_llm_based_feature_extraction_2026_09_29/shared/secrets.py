"""AWS Secrets Manager helpers for experiment API keys."""

from __future__ import annotations


def parse_secret_string(raw: str, keys: tuple[str, ...]) -> str:
    raise NotImplementedError


def ensure_openai_api_key() -> None:
    raise NotImplementedError
