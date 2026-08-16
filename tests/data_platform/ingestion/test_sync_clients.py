from __future__ import annotations

from unittest.mock import MagicMock, patch

from data_platform.ingestion.sync_clients import BLUESKY_PUBLIC_APPVIEW, init_bluesky_client


def test_init_bluesky_client_logs_in_when_credentials_are_set() -> None:
    def _get_env(name: str, required: bool = False) -> str:
        values = {
            "BLUESKY_HANDLE": "user.bsky.social",
            "BLUESKY_PASSWORD": "app-password",
        }
        return values.get(name, "")

    mock_client = MagicMock()
    with (
        patch(
            "data_platform.ingestion.sync_clients.EnvVarsContainer.get_env_var",
            side_effect=_get_env,
        ),
        patch("atproto.Client", return_value=mock_client) as client_cls,
    ):
        result = init_bluesky_client()

    assert result is mock_client
    client_cls.assert_called_once_with()
    mock_client.login.assert_called_once_with("user.bsky.social", "app-password")


def test_init_bluesky_client_uses_public_appview_when_credentials_missing() -> None:
    mock_client = MagicMock()
    with (
        patch(
            "data_platform.ingestion.sync_clients.EnvVarsContainer.get_env_var",
            return_value="",
        ),
        patch("atproto.Client", return_value=mock_client) as client_cls,
    ):
        result = init_bluesky_client()

    assert result is mock_client
    client_cls.assert_called_once_with(BLUESKY_PUBLIC_APPVIEW)
    mock_client.login.assert_not_called()
