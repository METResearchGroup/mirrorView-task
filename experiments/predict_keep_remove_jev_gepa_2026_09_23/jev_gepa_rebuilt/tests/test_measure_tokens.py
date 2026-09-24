"""Tests for union pair token measurement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.measure_tokens import (
    measure_union_pair_tokens,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import BatchResult


@dataclass
class FakeTokenScorer:
    """Returns fixed input token usage per batch."""

    input_tokens_per_post: int = 500
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(
        self,
        client: Any,
        state_texts: list[str],
        view: str,
        *,
        study_instruction: str,
        task_instruction: str | None = None,
    ) -> BatchResult:
        self.calls.append(
            {
                "n_posts": len(state_texts),
                "view": view,
                "study_instruction": study_instruction,
            }
        )
        n_posts = len(state_texts)
        total_in = self.input_tokens_per_post * n_posts
        return BatchResult(
            probabilities=[0.5] * n_posts,
            latency_ms=1.0,
            input_tokens=total_in,
            output_tokens=n_posts,
            model_version="fake-jev",
        )


class TestMeasureTokens:
    """Tests for measure_union_pair_tokens."""

    def test_mean_tokens_and_jev_cost_estimate(self) -> None:
        """Given fixed usage, mean tokens and 30k-post USD estimate match."""
        scorer = FakeTokenScorer(input_tokens_per_post=500)
        instances = [
            _fake_instance(f"p{i}") for i in range(20)
        ]
        result = measure_union_pair_tokens(
            instances,
            view="pair",
            n_posts=10,
            study_instruction="seed study text",
            scorer=scorer,
            rng_seed=20260924,
        )

        assert result["n_posts"] == 10
        assert result["mean_input_tokens_per_post"] == 500.0
        assert result["jev_optimize_usd_per_30k_posts"] > 0


def _fake_instance(post_id: str):
    from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevDataInst

    return JevDataInst(
        post_id=post_id,
        original_text="original",
        mirror_text="mirror",
        post_1_role="original",
        post_2_role="mirror",
        label=0,
        n_keep=6,
        n_remove=4,
        n_raters=10,
        remove_share=0.4,
        sampled_stance="left",
        sample_toxicity_type="low",
    )
