"""Tests for jev_gepa_rebuilt optimize CLI stub."""

from __future__ import annotations

import io
import sys
from unittest.mock import patch

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt import optimize


class TestOptimizeCli:
    """Tests for optimize.main CLI."""

    def test_help_lists_max_metric_calls_and_r1_ablation(self) -> None:
        """Verifies --help mentions --max-metric-calls and R1_gepa_pair."""
        buffer = io.StringIO()
        with patch.object(sys, "argv", ["optimize.py", "--help"]):
            with patch.object(sys, "stdout", buffer):
                with pytest.raises(SystemExit) as exc_info:
                    optimize.main(["--help"])
        assert exc_info.value.code == 0
        help_text = buffer.getvalue()
        assert "--max-metric-calls" in help_text
        assert "R1_gepa_pair" in help_text
