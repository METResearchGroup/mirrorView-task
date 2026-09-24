"""GEPA adapter for Jev keep/remove scoring.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_adapter.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from gepa.core.adapter import EvaluationBatch, GEPAAdapter
from typesafe_sdk import TypeSafeClient

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer, secrets
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import render_state_text
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter

ScoreMode = Literal["probability", "asymmetric"]
ViewName = Literal["pair", "original", "mirror"]

DEFAULT_THRESHOLD = 0.5
DEFAULT_BATCH_SIZE = 10
REMOVE_LABEL = 1


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
        self._scorer = scorer or jev_scorer.score_batch
        self._client = client
        self._lazy_client: TypeSafeClient | None = None
        self._rate_limiter = rate_limiter
        self._threshold = threshold
        self._batch_size = batch_size

    def _resolve_client(self) -> TypeSafeClient:
        if self._client is not None:
            return self._client
        if self._lazy_client is None:
            self._lazy_client = jev_scorer.build_client(secrets.get_jev_api_key())
        return self._lazy_client

    def _render_state_text(self, instance: JevDataInst) -> str:
        return render_state_text(
            self._view,
            instance.original_text,
            instance.mirror_text,
            instance.post_1_role,
            add_criteria=False,
        )

    def _wait_for_rate_limit(self) -> None:
        if self._rate_limiter is not None:
            self._rate_limiter.wait()

    def _call_scorer(
        self,
        state_texts: list[str],
        instruction: str,
    ) -> list[float]:
        self._wait_for_rate_limit()
        batch_result = self._scorer(
            self._resolve_client(),
            state_texts,
            self._view,
            instruction=instruction,
        )
        return [float(value) for value in batch_result.probabilities]

    def _probability_score(self, label: int, p_remove: float) -> float:
        if label == REMOVE_LABEL:
            return p_remove
        return 1.0 - p_remove

    def _score_example(
        self,
        instance: JevDataInst,
        p_remove: float,
    ) -> float:
        if self._score_mode == "probability":
            return self._probability_score(instance.label, p_remove)
        raise NotImplementedError("asymmetric score mode not implemented")

    def _build_trajectory(
        self,
        instance: JevDataInst,
        instruction: str,
        p_remove: float,
        error: str | None,
    ) -> JevTrajectory:
        predicted_remove = p_remove >= self._threshold
        gold_remove = instance.label == REMOVE_LABEL
        return JevTrajectory(
            post_id=instance.post_id,
            view=self._view,
            instruction=instruction,
            p_remove=p_remove,
            label=instance.label,
            n_keep=instance.n_keep,
            n_remove=instance.n_remove,
            sampled_stance=instance.sampled_stance,
            sample_toxicity_type=instance.sample_toxicity_type,
            threshold_crossed=predicted_remove != gold_remove,
            error=error,
        )

    def _score_instances(
        self,
        instances: list[JevDataInst],
        instruction: str,
        capture_traces: bool,
    ) -> tuple[list[JevRolloutOutput], list[float], list[JevTrajectory] | None, int]:
        outputs: list[JevRolloutOutput] = []
        scores: list[float] = []
        trajectories: list[JevTrajectory] | None = [] if capture_traces else None
        num_metric_calls = 0

        for chunk_start in range(0, len(instances), self._batch_size):
            chunk = instances[chunk_start : chunk_start + self._batch_size]
            state_texts = [self._render_state_text(instance) for instance in chunk]
            try:
                probabilities = self._call_scorer(state_texts, instruction)
                num_metric_calls += 1
                for instance, p_remove in zip(chunk, probabilities):
                    outputs.append(JevRolloutOutput(post_id=instance.post_id, p_remove=p_remove))
                    scores.append(self._score_example(instance, p_remove))
                    if trajectories is not None:
                        trajectories.append(
                            self._build_trajectory(instance, instruction, p_remove, None)
                        )
            except Exception as batch_error:
                for instance in chunk:
                    state_text = self._render_state_text(instance)
                    try:
                        p_remove = self._call_scorer([state_text], instruction)[0]
                        num_metric_calls += 1
                        outputs.append(
                            JevRolloutOutput(post_id=instance.post_id, p_remove=p_remove)
                        )
                        scores.append(self._score_example(instance, p_remove))
                        if trajectories is not None:
                            trajectories.append(
                                self._build_trajectory(instance, instruction, p_remove, None)
                            )
                    except Exception as post_error:
                        num_metric_calls += 1
                        outputs.append(JevRolloutOutput(post_id=instance.post_id, p_remove=0.0))
                        scores.append(0.0)
                        if trajectories is not None:
                            trajectories.append(
                                self._build_trajectory(
                                    instance,
                                    instruction,
                                    0.0,
                                    str(post_error),
                                )
                            )
                _ = batch_error
        return outputs, scores, trajectories, num_metric_calls

    def evaluate(
        self,
        batch: list[JevDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[JevTrajectory, JevRolloutOutput]:
        instruction = candidate["instruction"]
        outputs, scores, trajectories, num_metric_calls = self._score_instances(
            batch,
            instruction,
            capture_traces,
        )
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            num_metric_calls=num_metric_calls,
        )

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[JevTrajectory, JevRolloutOutput],
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        raise NotImplementedError


def _implements_gepa_adapter(adapter: JevGepaAdapter) -> GEPAAdapter[JevDataInst, JevTrajectory, JevRolloutOutput]:
    return adapter
