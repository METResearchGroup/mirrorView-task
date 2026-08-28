"""Client initialization for platform sync ingestion scripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib.load_env_vars import EnvVarsContainer

if TYPE_CHECKING:
    import praw
    import tweepy
    from atproto import Client


def init_reddit_client() -> praw.Reddit:
    """Build a PRAW Reddit instance using script-app password grant credentials."""
    import praw

    client_id = EnvVarsContainer.get_env_var("REDDIT_CLIENT_ID", required=True)
    client_secret = EnvVarsContainer.get_env_var("REDDIT_SECRET", required=True)
    username = EnvVarsContainer.get_env_var("REDDIT_USERNAME", required=True)
    password = EnvVarsContainer.get_env_var("REDDIT_PASSWORD", required=True)
    user_agent = f"lab_data_integrations:v0.1 (by /u/{username})"
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=user_agent,
    )


BLUESKY_PUBLIC_APPVIEW = "https://api.bsky.app"


def init_bluesky_client() -> Client:
    """Return an atproto Client for Bluesky keyword search.

    When BLUESKY_HANDLE and BLUESKY_PASSWORD are both set, log in on the
    default PDS. When they are missing, use the public AppView host, which
    serves searchPosts without an account.
    """
    from atproto import Client

    handle = EnvVarsContainer.get_env_var("BLUESKY_HANDLE", required=False).strip()
    password = EnvVarsContainer.get_env_var("BLUESKY_PASSWORD", required=False).strip()
    if bool(handle) != bool(password):
        raise ValueError(
            "BLUESKY_HANDLE and BLUESKY_PASSWORD must both be set, or both be unset. "
            "When both are unset, keyword search uses the public Bluesky API at "
            f"{BLUESKY_PUBLIC_APPVIEW}."
        )
    if handle and password:
        client = Client()
        client.login(handle, password)
        return client
    return Client(BLUESKY_PUBLIC_APPVIEW)


def init_twitter_client() -> tweepy.Client:
    """Build a Tweepy Client using app-only Bearer Token auth."""
    import tweepy

    bearer_token = EnvVarsContainer.get_env_var("X_BEARER_TOKEN", required=True)
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
