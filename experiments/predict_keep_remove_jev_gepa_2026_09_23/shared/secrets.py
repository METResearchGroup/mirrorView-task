"""Resolve API keys from environment variables or AWS Secrets Manager.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_secrets.py -q
"""

from __future__ import annotations

import json
import os

import boto3

from lib.load_env_vars import EnvVarsContainer

AWS_SECRETS_REGION = "us-east-2"
_JEV_SECRET_ID = "jev-typesafe-api-key"
_WANDB_SECRET_ID = "wandb-api-key"
_OPENAI_SECRET_ID = "openai-api-key"
_JEV_ENV_VAR = "TYPESAFE_API_KEY"


def _parse_secret_string(raw: str) -> str:
    stripped = raw.strip()
    if not stripped:
        return ""
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if not isinstance(data, dict):
        return stripped
    for key in ("api_key", "TYPESAFE_API_KEY", "key"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value)
    if not data:
        return ""
    return str(next(iter(data.values())))


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
    if env_var is not None:
        env_value = os.environ.get(env_var, "").strip()
        if env_value:
            return env_value

    client = boto3.client("secretsmanager", region_name=AWS_SECRETS_REGION)
    raw = client.get_secret_value(SecretId=secret_id)["SecretString"]
    parsed = _parse_secret_string(raw)
    if not parsed:
        raise ValueError(f"secret {secret_id} is empty or missing")
    return parsed


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
    return get_secret_value(_JEV_SECRET_ID, env_var=_JEV_ENV_VAR)


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
    env_value = EnvVarsContainer.get_env_var("WANDB_API_KEY", required=False).strip()
    if env_value:
        return env_value
    return get_secret_value(_WANDB_SECRET_ID)


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
    env_value = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=False).strip()
    if env_value:
        return env_value
    return get_secret_value(_OPENAI_SECRET_ID)
