"""Tests for the training-set experiment CLI and stubs."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.create_feature_generation_training_sets_2026_09_04.main import main
from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    DEFAULT_DATA_ROOT,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.walk import (
    build_training_sets,
)


class TestBuildTrainingSets:
    """Tests for build_training_sets."""

    def test_build_training_sets_raises_not_implemented(self, tmp_path: Path):
        """Verify the walk stub is not implemented yet."""
        with pytest.raises(NotImplementedError):
            build_training_sets(
                tmp_path,
                timestamp="2026_09_04-12:00:00",
                output_root=tmp_path / "training_data",
            )


class TestMain:
    """Tests for main."""

    @patch(
        "experiments.create_feature_generation_training_sets_2026_09_04.main.build_training_sets",
        side_effect=NotImplementedError,
    )
    @patch("pathlib.Path.iterdir")
    def test_main_calls_build_training_sets_without_reading_data_root(
        self,
        mock_iterdir,
        mock_build_training_sets,
    ):
        """Verify main delegates to build_training_sets and does not walk the data root."""
        with pytest.raises(NotImplementedError):
            main([])

        mock_build_training_sets.assert_called_once()
        mock_iterdir.assert_not_called()

        call_args, call_kwargs = mock_build_training_sets.call_args
        assert call_args[0] == DEFAULT_DATA_ROOT
        assert "timestamp" in call_kwargs
        assert "output_root" in call_kwargs
