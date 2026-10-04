"""W&B Weave setup for the DSPy GEPA experiment.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import weave

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    AWS_REGION,
    WANDB_PROJECT_PATH,
)
from lib.load_env_vars import EnvVarsContainer

SECRET_NAME_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "AUTHORIZATION", "CREDENTIAL")
LAB_ACCESS_KEY_NAME = "LAB_AWS_ACCESS_KEY_ID"
LAB_SECRET_KEY_NAME = "LAB_AWS_ACCESS_KEY_SECRET"
STANDARD_ACCESS_KEY_NAME = "AWS_ACCESS_KEY_ID"
STANDARD_SECRET_KEY_NAME = "AWS_SECRET_ACCESS_KEY"


def apply_lab_aws_credentials() -> None:
    """Copy lab AWS keys into the standard variables when those are empty."""
    _copy_when_empty(STANDARD_ACCESS_KEY_NAME, LAB_ACCESS_KEY_NAME)
    _copy_when_empty(STANDARD_SECRET_KEY_NAME, LAB_SECRET_KEY_NAME)
    os.environ.setdefault("AWS_DEFAULT_REGION", AWS_REGION)
    os.environ.setdefault("AWS_REGION", AWS_REGION)


def _copy_when_empty(target_name: str, source_name: str) -> None:
    if os.environ.get(target_name):
        return
    source_value = os.environ.get(source_name, "")
    if source_value:
        os.environ[target_name] = source_value


def require_wandb_api_key() -> None:
    """Load ``WANDB_API_KEY`` through the repository environment loader.

    Raises
    ------
    ValueError
        When the loader does not have a non-empty key.
    """
    EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)


def redact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return metadata with secret-like names removed."""
    return {
        key: value
        for key, value in metadata.items()
        if not _is_secret_name(key)
    }


def _is_secret_name(name: str) -> bool:
    upper_name = name.upper()
    return any(marker in upper_name for marker in SECRET_NAME_MARKERS)


def initialize_weave() -> Any:
    """Start Weave on the default host for the experiment project.

    Returns
    -------
    weave.trace.weave_client.WeaveClient
        Initialized client. Call ``finish`` after the stage flushes.
    """
    require_wandb_api_key()
    return weave.init(WANDB_PROJECT_PATH)


def trace_attributes(metadata: Mapping[str, Any]) -> Any:
    """Return a Weave attribute context with secrets removed."""
    return weave.attributes(redact_metadata(metadata))


@weave.op
def record_local_marker(stage: str) -> dict[str, str]:
    """Upload one no-cost local trace for a stage name."""
    return {"stage": stage, "paid": "false", "trace_url": call_url(weave.get_current_call())}


def call_url(call: Any) -> str:
    """Return the Weave UI URL for a completed call."""
    url = getattr(call, "ui_url", None)
    if url:
        return str(url)
    return str(call)
