"""GEPA adapter for Jev keep/remove scoring.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_adapter.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from gepa.core.adapter import EvaluationBatch, GEPAAdapter
from typesafe_sdk import TypeSafeClient

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter

ScoreMode = Literal["probability", "asymmetric"]
ViewName = Literal["pair", "original", "mirror"]

DEFAULT_THRESHOLD = 0.5
DEFAULT_BATCH_SIZE = 10


@dataclass(frozen=True)
class JevDataInst:
    post_id: str
    original_text: str
    mirror_text: str
    post_1_role: str
    post_2_role: str
    label: int
    n_keep: int
    n_remove: int
    n_raters: int
    sampled_stance: str
    sample_toxicity_type: str


@dataclass(frozen=True)
class JevTrajectory:
    post_id: str
    view: ViewName
    instruction: str
    p_remove: float
    label: int
    n_keep: int
    n_remove: int
    sampled_stance: str
    sample_toxicity_type: str
    threshold_crossed: bool
    error: str | None = None


@dataclass(frozen=True)
class JevRolloutOutput:
    post_id: str
    p_remove: float


class JevGepaAdapter:
    """Score Jev batches for GEPA with optional asymmetric reward mode."""

    def __init__(
        self,
        *,
        view: ViewName,
        score_mode: ScoreMode = "probability",
        scorer: Any | None = None,
        client: TypeSafeClient | None = None,
        rate_limiter: RequestStartLimiter | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._view = view
        self._score_mode = score_mode
        self._scorer = scorer
        self._client = client
        self._rate_limiter = rate_limiter
        self._threshold = threshold
        self._batch_size = batch_size

    def evaluate(
        self,
        batch: list[JevDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[JevTrajectory, JevRolloutOutput]:
        raise NotImplementedError

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[JevTrajectory, JevRolloutOutput],
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        raise NotImplementedError


def _implements_gepa_adapter(adapter: JevGepaAdapter) -> GEPAAdapter[JevDataInst, JevTrajectory, JevRolloutOutput]:
    return adapter
