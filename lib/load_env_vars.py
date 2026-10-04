"""Centralized environment variable loading.

Values come from AWS Secrets Manager in ``us-east-2``.

``get_env_var`` writes a resolved secret back into ``os.environ`` under the
public name. SDKs such as OpenAI read ``OPENAI_API_KEY`` from the process
environment after the presence check.

Public API: EnvVarsContainer.get_env_var(name, required=False)
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Final, NamedTuple

AWS_SECRETS_REGION: Final[str] = "us-east-2"


class SecretRef(NamedTuple):
    """Where one public environment variable lives in Secrets Manager."""

    secret_id: str
    key: str | None = None


# Public name -> secret id and JSON key. ``key is None`` means the secret
# string itself is the value (not a JSON object).
ENV_VAR_SOURCES: Final[dict[str, SecretRef]] = {
    "OPENAI_API_KEY": SecretRef("openai-api-key", "OPENAI_API_KEY"),
    "WANDB_API_KEY": SecretRef("wandb-api-key", "WANDB_API_KEY"),
    "GOOGLE_API_KEY": SecretRef("google-api-key", "GOOGLE_API_KEY"),
    "HF_TOKEN": SecretRef("huggingface-token", "HF_TOKEN"),
    "GH_TOKEN": SecretRef("github-pat-token", "GH_TOKEN"),
    "TYPESAFE_API_KEY": SecretRef("jev-typesafe-api-key", "TYPESAFE_API_KEY"),
    "BLUESKY_HANDLE": SecretRef("bluesky_account_credentials", "bluesky_handle"),
    "BLUESKY_PASSWORD": SecretRef("bluesky_account_credentials", "bluesky_password"),
    "BSKY_INTERNAL_API_KEY": SecretRef(
        "bsky-internal-api-key", "BSKY_INTERNAL_API_KEY"
    ),
    "X_BEARER_TOKEN": SecretRef("twitter-api-keys", "X_BEARER_TOKEN"),
    "X_CONSUMER_KEY": SecretRef("twitter-api-keys", "X_CONSUMER_KEY"),
    "X_SECRET_KEY": SecretRef("twitter-api-keys", "X_SECRET_KEY"),
    "MOMENTO_API_KEY": SecretRef("momento_credentials", "MOMENTO_API_KEY"),
    "MOMENTO_HTTP_ENDPOINT": SecretRef("momento_credentials", "MOMENTO_HTTP_ENDPOINT"),
    "APP_BEARER_TOKEN": SecretRef("lab-ml-api-token", "APP_BEARER_TOKEN"),
    "FEED_API_DEFAULT_TEST_TOKEN": SecretRef(
        "feed-api-default-test-token",
        "feed-api-default-test-token",
    ),
    "WEBSITE_PRIVATE_KEY_PEM": SecretRef("website_private_key_pem"),
    # Secret field is AWS_ACCESS_KEY_ID. Callers ask for AWS_ACCESS_KEY.
    "AWS_ACCESS_KEY": SecretRef("aws-credentials", "AWS_ACCESS_KEY_ID"),
    "AWS_ACCESS_KEY_SECRET": SecretRef("aws-credentials", "AWS_ACCESS_KEY_SECRET"),
}


class EnvVarsContainer:
    """Thread-safe singleton container for environment variables."""

    _instance: EnvVarsContainer | None = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._env_vars: dict[str, str | None] = {}
        self._secret_payloads: dict[str, dict[str, Any] | str] = {}
        self._client: Any = None
        self._init_lock = threading.Lock()

    @classmethod
    def get_env_var(cls, name: str, required: bool = False) -> str:
        """Get an environment variable after resolving Secrets Manager.

        Args:
            name: Environment variable name.
            required: If True, raises ValueError when missing or empty.

        Returns:
            The resolved string, or "" when the name is missing and not required.
        """
        instance: EnvVarsContainer = cls._get_instance()
        raw: str | None = instance._resolve(name)

        if required:
            if raw is None:
                raise ValueError(
                    f"{name} is required but is missing. "
                    f"Please set the {name} environment variable."
                )
            if isinstance(raw, str) and not raw.strip():
                raise ValueError(
                    f"{name} is required but is empty. "
                    f"Please set the {name} environment variable to a non-empty value."
                )

        if raw is None:
            return ""
        return str(raw)

    @classmethod
    def _get_instance(cls) -> EnvVarsContainer:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _resolve(self, name: str) -> str | None:
        cached = self._env_vars.get(name, _MISSING)
        if cached is not _MISSING:
            return cached
        with self._init_lock:
            cached = self._env_vars.get(name, _MISSING)
            if cached is not _MISSING:
                return cached
            from_env = os.getenv(name)
            if from_env is not None and from_env.strip():
                self._env_vars[name] = from_env
                return from_env
            source = ENV_VAR_SOURCES.get(name)
            if source is None:
                self._env_vars[name] = None
                return None
            value = self._value_from_secret(source)
            self._env_vars[name] = value
            if value:
                os.environ[name] = value
            return value

    def _secrets_client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "secretsmanager",
                region_name=AWS_SECRETS_REGION,
            )
        return self._client

    def _load_secret(self, secret_id: str) -> dict[str, Any] | str:
        cached = self._secret_payloads.get(secret_id)
        if cached is not None:
            return cached
        from botocore.exceptions import ClientError

        try:
            response = self._secrets_client().get_secret_value(SecretId=secret_id)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise ValueError(
                f"Failed to load secret {secret_id} from AWS Secrets Manager ({code})."
            ) from exc
        secret_string = response.get("SecretString")
        if not isinstance(secret_string, str) or not secret_string.strip():
            raise ValueError(f"Secret {secret_id} has no SecretString.")
        stripped = secret_string.strip()
        if stripped.startswith("{"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Secret {secret_id} is not valid JSON.") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Secret {secret_id} JSON must be an object.")
            self._secret_payloads[secret_id] = payload
            return payload
        self._secret_payloads[secret_id] = stripped
        return stripped

    def _value_from_secret(self, source: SecretRef) -> str:
        payload = self._load_secret(source.secret_id)
        if source.key is None:
            if not isinstance(payload, str):
                raise ValueError(
                    f"Secret {source.secret_id} is a JSON object, so it needs a key."
                )
            return payload
        if not isinstance(payload, dict):
            raise ValueError(
                f"Secret {source.secret_id} is a plain string and has no key {source.key}."
            )
        value = payload.get(source.key)
        if value is None or not str(value).strip():
            raise ValueError(
                f"Secret {source.secret_id} has no non-empty key {source.key}."
            )
        return str(value).strip()


class _Missing:
    """Sentinel for a name that has not been resolved yet."""


_MISSING = _Missing()
