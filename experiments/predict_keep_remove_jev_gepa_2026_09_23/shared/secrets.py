"""Resolve API keys from environment variables or AWS Secrets Manager.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_secrets.py -q
"""

from __future__ import annotations

AWS_SECRETS_REGION = "us-east-2"


def get_secret_value(secret_id: str, *, env_var: str | None = None) -> str:
    """Return env var when set and non-empty; else fetch Secrets Manager secret.

    Parameters
    ----------
    secret_id
        AWS Secrets Manager secret id.
    env_var
        Optional environment variable checked before Secrets Manager.

    Returns
    -------
    str
        Resolved secret value.

    Raises
    ------
    ValueError
        When both the environment variable and Secrets Manager value are empty.
    """
    raise NotImplementedError


def get_jev_api_key() -> str:
    """Return Jev TypeSafe API key from TYPESAFE_API_KEY env or secret jev-typesafe-api-key.

    Returns
    -------
    str
        Jev TypeSafe API key.

    Raises
    ------
    ValueError
        When the key cannot be resolved.
    """
    raise NotImplementedError


def get_wandb_api_key() -> str:
    """Return Wandb API key from WANDB_API_KEY env or secret wandb-api-key.

    Returns
    -------
    str
        Wandb API key.

    Raises
    ------
    ValueError
        When the key cannot be resolved.
    """
    raise NotImplementedError


def get_openai_api_key() -> str:
    """Return OpenAI API key from OPENAI_API_KEY env or secret openai-api-key.

    Returns
    -------
    str
        OpenAI API key.

    Raises
    ------
    ValueError
        When the key cannot be resolved.
    """
    raise NotImplementedError
