"""Tests for parse_args()."""

import pytest

from experiments.generate_study_user_assignments_2026_09_08.constants import (
    PINNED_REMAINING_LABELS_S3_URI,
)
from experiments.generate_study_user_assignments_2026_09_08.run import parse_args


class TestParseArgs:
    """Tests for parse_args()."""

    def test_missing_remaining_labels_exits_and_names_pinned_uri(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verifies omitting --remaining-labels exits non-zero and names the pinned URI."""
        with pytest.raises(SystemExit) as raised:
            parse_args([])

        captured = capsys.readouterr()
        assert raised.value.code != 0
        assert PINNED_REMAINING_LABELS_S3_URI in captured.err + captured.out

    def test_local_path_is_returned(self, tmp_path) -> None:
        """Verifies a local remaining-labels path is parsed."""
        remaining_path = tmp_path / "remaining.csv"
        remaining_path.write_text("id,number_of_times_to_label,batch\n")

        result = parse_args(["--remaining-labels", str(remaining_path)])

        assert result.remaining_labels == str(remaining_path)
