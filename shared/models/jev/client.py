"""TypeSafe API key lookup and ``TypeSafeClassifier`` construction.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.client import build_jev_classifier, get_jev_api_key; print(get_jev_api_key.__name__)"
"""

from __future__ import annotations

import json
import os

import boto3
from langchain_typesafe import TypeSafeClassifier

from shared.data.dataloader import _use_lab_credentials_when_unset
from shared.models.jev.constants import (
    JEV_MODEL_ID,
    JEV_REQUEST_TIMEOUT_SECONDS,
    JEV_SECRET_ID,
    JEV_SECRETS_REGION,
)

_SECRET_KEYS = ("api_key", "TYPESAFE_API_KEY", "key")


def get_jev_api_key() -> str:
    """Return the TypeSafe API key from ``TYPESAFE_API_KEY`` or Secrets Manager.

    Returns
    -------
    str
        Stripped API key. The key is never logged.

    Raises
    ------
    ValueError
        When the secret is empty or has none of the expected JSON keys.
    """
    from_env = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if from_env:
        return from_env
    _use_lab_credentials_when_unset()
    client = boto3.client("secretsmanager", region_name=JEV_SECRETS_REGION)
    raw = (client.get_secret_value(SecretId=JEV_SECRET_ID).get("SecretString") or "").strip()
    if not raw:
        raise ValueError(f"secret {JEV_SECRET_ID} has no SecretString")
    if not raw.startswith("{"):
        return raw
    payload = json.loads(raw)
    for key in _SECRET_KEYS:
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    raise ValueError(f"secret {JEV_SECRET_ID} has none of {_SECRET_KEYS}")


def build_jev_classifier(
    model_id: str = JEV_MODEL_ID,
    api_key: str | None = None,
    timeout: float = JEV_REQUEST_TIMEOUT_SECONDS,
) -> TypeSafeClassifier:
    """Build a classifier pinned to ``model_id``. Looks up the key when omitted.

    Parameters
    ----------
    model_id
        TypeSafe model ID to pin.
    api_key
        Explicit API key. When omitted, the key is loaded from the environment
        or Secrets Manager.
    timeout
        Request timeout in seconds.

    Returns
    -------
    TypeSafeClassifier
        Classifier configured for one pinned model.
    """
    return TypeSafeClassifier(
        model=model_id,
        api_key=api_key if api_key is not None else get_jev_api_key(),
        timeout=timeout,
    )
