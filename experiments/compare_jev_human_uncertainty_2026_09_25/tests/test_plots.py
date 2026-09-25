"""Tests for the comparison figures.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.plots import write_figures

_PNG_MAGIC = b"\x89PNG"


def _comparison_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["a", "b"],
            "n_remove": [0, 1],
            "p_remove": [0.1, 0.85],
            "jev_bin": [0, 4],
            "difference_score": [0, -3],
        }
    )


class TestWriteFigures:
    """Tests for write_figures."""

    def test_writes_five_pngs(self, tmp_path: Path) -> None:
        """Writes five PNG files that start with the PNG magic bytes."""
        result = write_figures(_comparison_frame(), tmp_path)
        expected_count = 5

        assert len(result) == expected_count
        for path in result:
            assert path.is_file()
            assert path.read_bytes().startswith(_PNG_MAGIC)
