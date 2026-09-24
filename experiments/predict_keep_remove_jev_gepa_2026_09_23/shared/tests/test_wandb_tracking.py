"""Tests for Wandb run initialization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import (
    WANDB_ENTITY,
    WANDB_PROJECT,
    WandbRunSpec,
    init_run,
)


class TestInitRun:
    """Tests for init_run."""

    def test_initializes_wandb_with_project_conventions(self) -> None:
        """Verifies wandb.login and wandb.init use the experiment conventions."""
        spec = WandbRunSpec(
            group="jev_baseline",
            name="A1_pair_study_prompt",
            job_type="score",
            config={},
        )
        mock_run = MagicMock()

        with (
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking.get_wandb_api_key",
                return_value="wandb-key",
            ),
            patch("wandb.login") as mock_login,
            patch("wandb.init", return_value=mock_run) as mock_init,
        ):
            result = init_run(spec)

        assert result is mock_run
        mock_login.assert_called_once_with(key="wandb-key")
        mock_init.assert_called_once()
        init_kwargs = mock_init.call_args.kwargs
        assert init_kwargs["project"] == WANDB_PROJECT
        assert init_kwargs["entity"] == WANDB_ENTITY
        assert init_kwargs["group"] == "jev_baseline"
        assert init_kwargs["name"] == "A1_pair_study_prompt"
        assert init_kwargs.get("job_type") == "score" or init_kwargs.get("config", {}).get(
            "job_type"
        ) == "score" or "score" in init_kwargs.get("tags", [])
