"""AWS Secrets Manager helpers for experiment API keys."""

from __future__ import annotations

import json
import os

import boto3

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    AWS_SECRETS_REGION,
    OPENAI_SECRET_ID,
)


def parse_secret_string(raw: str, keys: tuple[str, ...]) -> str:
    """Parse a plain-text or JSON secret string.

    Parameters
    ----------
    raw
        Secret payload from Secrets Manager.
    keys
        JSON object keys to try in order when ``raw`` is a JSON object.

    Returns
    -------
    str
        The selected secret value.

    Raises
    ------
    ValueError
        When no non-empty value is found.
    """
    stripped = raw.strip()
    if not stripped.startswith("{"):
        if not stripped:
            raise ValueError("secret string is empty")
        return stripped
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("secret JSON must be an object")
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ValueError(f"no non-empty value among keys {keys}")


def ensure_openai_api_key() -> None:
    """Load ``OPENAI_API_KEY`` from Secrets Manager into the environment.

    Always fetches the secret, even when ``OPENAI_API_KEY`` is already set.
    """
    use_lab_credentials()
    os.environ["AWS_DEFAULT_REGION"] = AWS_SECRETS_REGION
    client = boto3.client("secretsmanager", region_name=AWS_SECRETS_REGION)
    response = client.get_secret_value(SecretId=OPENAI_SECRET_ID)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"secret {OPENAI_SECRET_ID} has no SecretString")
    api_key = parse_secret_string(secret_string, ("api_key", "OPENAI_API_KEY"))
    os.environ["OPENAI_API_KEY"] = api_key
