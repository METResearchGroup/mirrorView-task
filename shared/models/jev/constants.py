"""Jev model, secret, and request settings for shared scoring.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.constants import JEV_MODEL_ID; print(JEV_MODEL_ID)"
"""

JEV_MODEL_ID = "jev-1.13.0"
JEV_SECRET_ID = "jev-typesafe-api-key"
JEV_SECRETS_REGION = "us-east-2"
JEV_REQUEST_TIMEOUT_SECONDS = 120.0
JEV_RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
JEV_MAX_REQUESTS_PER_MINUTE = 1000
JEV_USD_PER_MILLION_INPUT = 0.042
JEV_USD_PER_MILLION_OUTPUT = 0.0
