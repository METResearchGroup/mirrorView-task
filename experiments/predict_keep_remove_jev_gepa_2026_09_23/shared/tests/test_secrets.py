"""Tests for API key resolution helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets import get_jev_api_key


class TestGetSecretValue:
    """Tests for get_jev_api_key and secret resolution."""

    def test_prefers_environment_over_secrets_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies TYPESAFE_API_KEY is returned without calling boto3."""
        monkeypatch.setenv("TYPESAFE_API_KEY", "abc")

        with patch("experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets.boto3") as mock_boto3:
            result = get_jev_api_key()

        assert result == "abc"
        mock_boto3.client.assert_not_called()

    def test_reads_raw_secret_string_from_secrets_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies a raw Secrets Manager string is returned when env is empty."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": "sk-test"}

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets.boto3.client",
            return_value=mock_client,
        ):
            result = get_jev_api_key()

        assert result == "sk-test"

    def test_reads_json_api_key_from_secrets_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies JSON secrets with api_key are parsed correctly."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"api_key": "from-json"}),
        }

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets.boto3.client",
            return_value=mock_client,
        ):
            result = get_jev_api_key()

        assert result == "from-json"

    def test_raises_when_secret_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies ValueError mentions the secret id when resolution fails."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": ""}

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets.boto3.client",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="jev-typesafe-api-key"):
                get_jev_api_key()
