"""Tests for stimulus and label loaders."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
)


class TestUnionRegistryNames:
    """Tests that loaders use the Part 2+3 union registry keys."""

    @patch("experiments.bertopic_original_mirror_part3_2026_09_24.src.data.load_dataset")
    def test_load_stimuli_posts_uses_union_stimuli(self, mock_load) -> None:
        """Stimuli load from STUDY_PHASE_2_PART_2_AND_3_STIMULI."""
        mock_load.return_value = pd.DataFrame(
            {
                "post_primary_key": ["a"],
                "original_text": ["orig"],
                "mirrored_text": ["mir"],
            }
        )

        data_mod.load_stimuli_posts()

        mock_load.assert_called_once_with(STUDY_PHASE_2_PART_2_AND_3_STIMULI, low_memory=False)

    @patch("experiments.bertopic_original_mirror_part3_2026_09_24.src.data.load_dataset")
    def test_load_keep_remove_posts_uses_union_labels(self, mock_load) -> None:
        """Keep/remove labels load from STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS."""
        mock_load.return_value = pd.DataFrame(
            {column: ["x"] for column in data_mod.KEEP_REMOVE_COLUMNS}
            | {"is_unanimous": [True]}
        )

        data_mod.load_keep_remove_posts()

        mock_load.assert_called_once_with(
            STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS,
            low_memory=False,
        )

    @patch("experiments.bertopic_original_mirror_part3_2026_09_24.src.data.load_dataset")
    def test_load_keep_remove_posts_raises_when_columns_missing(self, mock_load) -> None:
        """Slim or incomplete registry rows raise KeyError instead of rebuilding."""
        mock_load.return_value = pd.DataFrame(
            {
                "message_id": ["a"],
                "original_text": ["o"],
                "mirror_text": ["m"],
                "decision": ["keep"],
                "keep_remove_label": [0],
                "n_raters": [3],
            }
        )

        try:
            data_mod.load_keep_remove_posts()
        except KeyError as exc:
            assert "missing columns" in str(exc).lower()
        else:
            raise AssertionError("expected KeyError for slim keep/remove labels")
