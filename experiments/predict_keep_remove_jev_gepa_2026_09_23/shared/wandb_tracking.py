"""Wandb run initialization and artifact logging for the experiment.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_wandb_tracking.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

WANDB_PROJECT = "predict_keep_remove_jev_gepa_2026_09_23"
WANDB_ENTITY = "mind_technology_lab"


@dataclass(frozen=True)
class WandbRunSpec:
    """Configuration for initializing a Wandb run."""

    group: str
    name: str
    job_type: str
    config: dict[str, object]


def init_run(spec: WandbRunSpec) -> Any:
    """Call wandb.login then wandb.init for the experiment project.

    Parameters
    ----------
    spec
        Run group, name, job type, and config payload.

    Returns
    -------
    Any
        Active Wandb run handle.
    """
    raise NotImplementedError


def log_artifact(run: Any, path: Path, name: str, artifact_type: str) -> None:
    """Log a local file as a Wandb artifact on the active run.

    Parameters
    ----------
    run
        Active Wandb run returned by :func:`init_run`.
    path
        Local file to upload.
    name
        Artifact name.
    artifact_type
        Wandb artifact type label.
    """
    raise NotImplementedError
