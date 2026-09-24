"""GEPA adapter for rebuilt Jev keep/remove scoring with study-instruction optimization.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_adapter_scores.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from gepa.core.adapter import EvaluationBatch, GEPAAdapter
from typesafe_sdk import TypeSafeClient

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer, secrets
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    VIEW_MIRROR,
    VIEW_ORIGINAL,
    VIEW_PAIR,
    default_study_instruction_seed,
    render_posts_only_state,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries import run_with_retries

ScoreMode = Literal["label_certainty", "majority_weighted", "plain_majority"]
ViewName = Literal["pair", "original", "mirror"]

DEFAULT_THRESHOLD = 0.5
DEFAULT_BATCH_SIZE = 10
REMOVE_LABEL = 1
CONFIDENT_ERROR_MARGIN = 0.15


@dataclass(frozen=True)
class JevDataInst:
    """One GEPA evaluation instance with paired post texts and gold keep/remove label."""

    post_id: str
    original_text: str
    mirror_text: str
    post_1_role: str
    post_2_role: str
    label: int
    n_keep: int
    n_remove: int
    n_raters: int
    remove_share: float
    sampled_stance: str
    sample_toxicity_type: str


@dataclass(frozen=True)
class JevTrajectory:
    """Scored rollout trace for one instance, including threshold-crossing state."""

    post_id: str
    view: ViewName
    study_instruction: str
    original_text: str
    mirror_text: str
    p_remove: float
    label: int
    n_keep: int
    n_remove: int
    remove_share: float
    sampled_stance: str
    sample_toxicity_type: str
    threshold_crossed: bool
    error: str | None = None


@dataclass(frozen=True)
class JevRolloutOutput:
    """GEPA rollout output carrying the predicted P(remove) for one post."""

    post_id: str
    p_remove: float


def default_seed_candidate(view: ViewName) -> dict[str, str]:
    """Return the GEPA seed candidate with the study instruction component only."""
    return {STUDY_COMPONENT_KEY: default_study_instruction_seed(view)}


class JevGepaRebuiltAdapter:
    """Score Jev batches for rebuilt GEPA with study-instruction optimization."""

    propose_new_texts = None

    def __init__(
        self,
        *,
        view: ViewName,
        score_mode: ScoreMode = "label_certainty",
        scorer: Any | None = None,
        client: TypeSafeClient | None = None,
        rate_limiter: RequestStartLimiter | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._view = view
        self._score_mode = score_mode
        self._scorer = scorer or jev_scorer.score_batch_with_study_instruction
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
        return render_posts_only_state(
            self._view,
            instance.original_text,
            instance.mirror_text,
            instance.post_1_role,
        )

    def _wait_for_rate_limit(self) -> None:
        if self._rate_limiter is not None:
            self._rate_limiter.wait()

    def _call_scorer(
        self,
        state_texts: list[str],
        study_instruction: str,
    ) -> list[float]:
        def _attempt() -> list[float]:
            self._wait_for_rate_limit()
            batch_result = self._scorer(
                self._resolve_client(),
                state_texts,
                self._view,
                study_instruction=study_instruction,
            )
            return [float(value) for value in batch_result.probabilities]

        return run_with_retries(_attempt)

    def _majority_probability(self, label: int, p_remove: float) -> float:
        if label == REMOVE_LABEL:
            return p_remove
        return 1.0 - p_remove

    def _vote_margin_weight(self, n_keep: int, n_remove: int) -> float:
        if abs(n_keep - n_remove) == 1:
            return 0.5
        return 1.0

    def _score_example(
        self,
        instance: JevDataInst,
        p_remove: float,
    ) -> float:
        if self._score_mode == "label_certainty":
            return 1.0 - abs(p_remove - instance.remove_share)
        majority_prob = self._majority_probability(instance.label, p_remove)
        if self._score_mode == "plain_majority":
            return majority_prob
        return majority_prob * self._vote_margin_weight(instance.n_keep, instance.n_remove)

    def _is_confident_error(self, trajectory: JevTrajectory) -> bool:
        if not trajectory.threshold_crossed:
            return False
        distance_from_even = abs(trajectory.p_remove - 0.5)
        return distance_from_even >= CONFIDENT_ERROR_MARGIN

    def _build_trajectory(
        self,
        instance: JevDataInst,
        study_instruction: str,
        p_remove: float,
        error: str | None,
    ) -> JevTrajectory:
        predicted_remove = p_remove >= self._threshold
        gold_remove = instance.label == REMOVE_LABEL
        return JevTrajectory(
            post_id=instance.post_id,
            view=self._view,
            study_instruction=study_instruction,
            original_text=instance.original_text,
            mirror_text=instance.mirror_text,
            p_remove=p_remove,
            label=instance.label,
            n_keep=instance.n_keep,
            n_remove=instance.n_remove,
            remove_share=instance.remove_share,
            sampled_stance=instance.sampled_stance,
            sample_toxicity_type=instance.sample_toxicity_type,
            threshold_crossed=predicted_remove != gold_remove,
            error=error,
        )

    def _score_instances(
        self,
        instances: list[JevDataInst],
        study_instruction: str,
        capture_traces: bool,
    ) -> tuple[list[JevRolloutOutput], list[float], list[JevTrajectory] | None, int]:
        outputs: list[JevRolloutOutput] = []
        scores: list[float] = []
        trajectories: list[JevTrajectory] | None = [] if capture_traces else None
        num_metric_calls = 0

        for chunk_start in range(0, len(instances), self._batch_size):
            chunk = instances[chunk_start : chunk_start + self._batch_size]
            state_texts = [self._render_state_text(instance) for instance in chunk]
            probabilities = self._call_scorer(state_texts, study_instruction)
            num_metric_calls += len(chunk)
            for instance, p_remove in zip(chunk, probabilities):
                outputs.append(JevRolloutOutput(post_id=instance.post_id, p_remove=p_remove))
                scores.append(self._score_example(instance, p_remove))
                if trajectories is not None:
                    trajectories.append(
                        self._build_trajectory(instance, study_instruction, p_remove, None)
                    )
        return outputs, scores, trajectories, num_metric_calls

    def evaluate(
        self,
        batch: list[JevDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[JevTrajectory, JevRolloutOutput]:
        """Score a candidate study instruction on a batch and return GEPA results."""
        study_instruction = candidate[STUDY_COMPONENT_KEY]
        outputs, scores, trajectories, num_metric_calls = self._score_instances(
            batch,
            study_instruction,
            capture_traces,
        )
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            num_metric_calls=num_metric_calls,
        )

    def _build_reflective_inputs(self, trajectory: JevTrajectory) -> dict[str, str]:
        if self._view == VIEW_PAIR:
            return {
                "original_text": trajectory.original_text,
                "mirror_text": trajectory.mirror_text,
            }
        if self._view == VIEW_ORIGINAL:
            return {"post_text": trajectory.original_text}
        if self._view == VIEW_MIRROR:
            return {"post_text": trajectory.mirror_text}
        raise ValueError(f"unknown view: {self._view}")

    def _build_feedback(self, trajectory: JevTrajectory) -> str:
        predicted_label = REMOVE_LABEL if trajectory.p_remove >= self._threshold else 0
        vote_margin = abs(trajectory.n_keep - trajectory.n_remove)
        confident_error = self._is_confident_error(trajectory)
        return (
            f"Gold label={trajectory.label} ({'remove' if trajectory.label == REMOVE_LABEL else 'keep'}). "
            f"Human votes: keep={trajectory.n_keep}, remove={trajectory.n_remove}. "
            f"remove_share={trajectory.remove_share:.3f}. "
            f"vote_margin={vote_margin}. "
            f"confident_error={confident_error}. "
            f"Sampled stance={trajectory.sampled_stance}. "
            f"Toxicity={trajectory.sample_toxicity_type}. "
            f"P(remove)={trajectory.p_remove:.3f}; predicted_label={predicted_label}. "
            f"Threshold crossed={trajectory.threshold_crossed} at threshold={self._threshold}."
        )

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[JevTrajectory, JevRolloutOutput],
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build reflective-dataset records from scored trajectories for study updates."""
        if eval_batch.trajectories is None:
            raise ValueError("eval_batch.trajectories is required for reflection")
        records: list[dict[str, Any]] = []
        for trajectory in eval_batch.trajectories:
            predicted_label = (
                REMOVE_LABEL if trajectory.p_remove >= self._threshold else 0
            )
            records.append(
                {
                    "Inputs": self._build_reflective_inputs(trajectory),
                    "Generated Outputs": {
                        "p_remove": f"{trajectory.p_remove:.3f}",
                        "predicted_label": str(predicted_label),
                    },
                    "Feedback": self._build_feedback(trajectory),
                }
            )
        if STUDY_COMPONENT_KEY not in components_to_update:
            return {}
        return {STUDY_COMPONENT_KEY: records}


def _implements_gepa_adapter(
    adapter: JevGepaRebuiltAdapter,
) -> GEPAAdapter[JevDataInst, JevTrajectory, JevRolloutOutput]:
    return adapter
