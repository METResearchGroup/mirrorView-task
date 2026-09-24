"""Tests for Part 2 theme mapping."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.map_part2_themes import (
    embed_feature_text,
    load_part2_themes,
    rank1_theme_map_rows,
    write_theme_map_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PART2_THEMES_DIR = REPO_ROOT / constants.PART2_STAGE2_OUTPUT_DIR


class TestLoadPart2Themes:
    """Tests for load_part2_themes."""

    def test_load_part2_themes_reads_132_themes(self) -> None:
        themes = load_part2_themes(PART2_THEMES_DIR)
        assert len(themes) == 132
        assert all(theme.theme_id and theme.label for theme in themes)


class TestEmbedFeatureText:
    """Tests for embed_feature_text."""

    def test_map_part2_embeds_name_plus_definition(self) -> None:
        result = embed_feature_text("Name", "Definition")
        assert result == "Name. Definition"


class TestRank1ThemeMap:
    """Tests for rank-1 theme mapping."""

    def test_map_part2_writes_rank1_table(self, tmp_path: Path) -> None:
        themes = [
            load_part2_themes(PART2_THEMES_DIR)[0],
            load_part2_themes(PART2_THEMES_DIR)[1],
        ]
        features = [
            {"feature_id": "cb_001", "name": "A", "definition": "alpha"},
            {"feature_id": "cb_002", "name": "B", "definition": "beta"},
            {"feature_id": "cb_003", "name": "C", "definition": "gamma"},
        ]

        def mock_embed(text: str) -> list[float]:
            if text.startswith("A."):
                return [1.0, 0.0]
            if text.startswith("B."):
                return [0.0, 1.0]
            if text.startswith("C."):
                return [0.7, 0.7]
            return [0.0, 0.0]

        rows = rank1_theme_map_rows(features, themes, mock_embed)
        run_dir = tmp_path / "map"
        csv_path = write_theme_map_outputs(run_dir, rows, PART2_THEMES_DIR, len(themes))
        frame = pd.read_csv(csv_path)
        assert list(frame.columns) == [
            "feature_id",
            "feature_name",
            "part2_theme_id",
            "part2_theme_label",
            "cosine_similarity",
            "rank",
        ]
        assert (frame["rank"] == 1).all()
