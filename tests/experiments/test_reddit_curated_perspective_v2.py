"""Tests for the Reddit curated Perspective v2 load and scoring helpers."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from data_platform.generate_features.models import LabelTask
from data_platform.utils.object_store import sha256_hex
from experiments.reddit_curated_perspective_v2_2026_09_08 import load_curated
from experiments.reddit_curated_perspective_v2_2026_09_08 import run as experiment_run
from experiments.reddit_curated_perspective_v2_2026_09_08.load_curated import (
    LLM_TOXICITY_TIER_COLUMN,
    SOURCE_RECORD_ID_COLUMN,
    TEXT_COLUMN,
    load_pinned_curated,
    medium_rows,
)
from experiments.reddit_curated_perspective_v2_2026_09_08.promote_v2 import (
    V2_OBJECT_KEY,
    apply_promotions,
    select_promotions,
    write_curated_v2,
)
from experiments.reddit_curated_perspective_v2_2026_09_08.score_medium import (
    TOXICITY_PROB_COLUMN,
    default_score_engine,
    require_all_medium_scored,
    score_medium_comments,
    tasks_for_medium_rows,
)


@dataclass(frozen=True)
class FakeStoredObject:
    body: bytes
    etag: str = '"etag"'


class FakeStore:
    """Public test double for CampaignObjectStore.get, put_new, and replace."""

    def __init__(
        self, body: bytes, *, put_new_error: BaseException | None = None
    ) -> None:
        self.body = body
        self.put_new_calls: list[str] = []
        self.replace_calls: list[str] = []
        self.put_new_bodies: list[bytes] = []
        self.put_new_error = put_new_error

    def get(self, key: str) -> FakeStoredObject:
        del key
        return FakeStoredObject(body=self.body)

    def put_new(self, key: str, body: bytes, tags: dict[str, str] | None = None) -> None:
        del tags
        if self.put_new_error is not None:
            raise self.put_new_error
        self.put_new_calls.append(key)
        self.put_new_bodies.append(body)
        self.body = body

    def replace(self, key: str, body: bytes, *, etag: str | None = None) -> None:
        del body, etag
        self.replace_calls.append(key)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _curated_frame(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                SOURCE_RECORD_ID_COLUMN: source_record_id,
                TEXT_COLUMN: text,
                LLM_TOXICITY_TIER_COLUMN: tier,
            }
            for source_record_id, text, tier in rows
        ]
    )


class TestMediumRows:
    """Tests for medium_rows()."""

    def test_keeps_only_medium_tier_rows(self) -> None:
        """Keep the medium row and drop low and high."""
        curated = _curated_frame(
            [
                ("id-low", "civil text", "low"),
                ("id-medium", "rude text", "medium"),
                ("id-high", "threat text", "high"),
            ]
        )

        result = medium_rows(curated)

        expected = _curated_frame([("id-medium", "rude text", "medium")])
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


class TestLoadPinnedCurated:
    """Tests for load_pinned_curated()."""

    def test_returns_frame_when_hash_and_counts_match(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Accept a fake store body whose hash and medium count match the pinned checks."""
        curated = _curated_frame(
            [
                ("a", "text a", "low"),
                ("b", "text b", "medium"),
                ("c", "text c", "high"),
            ]
        )
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", sha256_hex(body))
        monkeypatch.setattr(load_curated, "EXPECTED_CURATED_ROW_COUNT", 3)
        monkeypatch.setattr(load_curated, "EXPECTED_MEDIUM_ROW_COUNT", 1)
        store = FakeStore(body)

        result = load_pinned_curated(store=store, cache_path=tmp_path / "curated.parquet")

        assert len(result) == 3
        assert store.put_new_calls == []

    def test_raises_when_hash_does_not_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reject bytes whose SHA-256 is not the pinned digest."""
        curated = _curated_frame([("a", "text a", "medium")])
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", "0" * 64)
        store = FakeStore(body)

        with pytest.raises(ValueError):
            load_pinned_curated(store=store)

        assert store.put_new_calls == []

    def test_raises_when_medium_count_is_wrong(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reject a table whose medium count does not match the pinned medium count."""
        curated = _curated_frame(
            [
                ("a", "text a", "medium"),
                ("b", "text b", "low"),
            ]
        )
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", sha256_hex(body))
        monkeypatch.setattr(load_curated, "EXPECTED_CURATED_ROW_COUNT", 2)
        monkeypatch.setattr(load_curated, "EXPECTED_MEDIUM_ROW_COUNT", 2)
        store = FakeStore(body)

        with pytest.raises(ValueError):
            load_pinned_curated(store=store, cache_path=tmp_path / "curated.parquet")


class RecordingEngine:
    """Records LabelTask batches and returns configured toxicity probabilities."""

    def __init__(self, toxicity_prob_by_id: dict[str, float]) -> None:
        self.toxicity_prob_by_id = toxicity_prob_by_id
        self.received_tasks: list[LabelTask] = []

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        self.received_tasks.extend(tasks)
        return [
            {
                SOURCE_RECORD_ID_COLUMN: task.uri,
                TOXICITY_PROB_COLUMN: self.toxicity_prob_by_id[task.uri],
            }
            for task in tasks
            if task.uri in self.toxicity_prob_by_id
        ]


def _scores_frame(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                SOURCE_RECORD_ID_COLUMN: source_record_id,
                TOXICITY_PROB_COLUMN: toxicity_prob,
            }
            for source_record_id, toxicity_prob in rows
        ]
    )


def _write_scores(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _scores_frame(rows).to_parquet(path, index=False)


class TestTasksForMediumRows:
    """Tests for tasks_for_medium_rows()."""

    def test_builds_one_task_per_row_with_record_id_and_text(self) -> None:
        """Map each medium row to LabelTask.uri and LabelTask.text."""
        medium = _curated_frame(
            [
                ("id-1", "hello", "medium"),
                ("id-2", "bye", "medium"),
            ]
        )

        result = tasks_for_medium_rows(medium)

        expected = [
            LabelTask(uri="id-1", text="hello"),
            LabelTask(uri="id-2", text="bye"),
        ]
        assert result == expected

    def test_excludes_low_tier_ids_when_called_after_medium_rows(self) -> None:
        """Do not build tasks for low-tier ids after medium_rows()."""
        curated = _curated_frame(
            [
                ("id-low", "civil text", "low"),
                ("id-medium", "rude text", "medium"),
                ("id-high", "threat text", "high"),
            ]
        )

        result = tasks_for_medium_rows(medium_rows(curated))

        expected = [LabelTask(uri="id-medium", text="rude text")]
        assert result == expected


class TestScoreMediumComments:
    """Tests for score_medium_comments()."""

    def test_persists_probabilities_from_the_engine(self, tmp_path: Path) -> None:
        """Save every medium id and the fake engine's toxicity_prob."""
        medium = _curated_frame(
            [
                ("id-a", "text a", "medium"),
                ("id-b", "text b", "medium"),
                ("id-c", "text c", "medium"),
            ]
        )
        engine = RecordingEngine({"id-a": 0.2, "id-b": 0.8, "id-c": 0.5})
        scores_path = tmp_path / "medium_perspective_scores.parquet"

        result = score_medium_comments(medium, scores_path=scores_path, engine=engine)

        expected = _scores_frame([("id-a", 0.2), ("id-b", 0.8), ("id-c", 0.5)])
        saved = pd.read_parquet(scores_path)
        pd.testing.assert_frame_equal(
            result[[SOURCE_RECORD_ID_COLUMN, TOXICITY_PROB_COLUMN]].reset_index(drop=True),
            expected,
        )
        pd.testing.assert_frame_equal(
            saved[[SOURCE_RECORD_ID_COLUMN, TOXICITY_PROB_COLUMN]].reset_index(drop=True),
            expected,
        )
        assert [task.uri for task in engine.received_tasks] == ["id-a", "id-b", "id-c"]

    def test_skips_ids_that_already_have_a_unit_interval_probability(
        self, tmp_path: Path
    ) -> None:
        """Call the engine only for the medium id missing from the scores file."""
        medium = _curated_frame(
            [
                ("id-a", "text a", "medium"),
                ("id-b", "text b", "medium"),
                ("id-c", "text c", "medium"),
            ]
        )
        scores_path = tmp_path / "medium_perspective_scores.parquet"
        _write_scores(scores_path, [("id-a", 0.2), ("id-c", 0.5)])
        engine = RecordingEngine({"id-b": 0.8})

        result = score_medium_comments(medium, scores_path=scores_path, engine=engine)

        expected_ids = {"id-a", "id-b", "id-c"}
        assert set(result[SOURCE_RECORD_ID_COLUMN].astype(str)) == expected_ids
        assert len(result) == 3
        assert [task.uri for task in engine.received_tasks] == ["id-b"]
        saved = pd.read_parquet(scores_path)
        assert set(saved[SOURCE_RECORD_ID_COLUMN].astype(str)) == expected_ids

    def test_raises_when_the_engine_omits_an_id(self, tmp_path: Path) -> None:
        """Raise ValueError when a medium id still has no probability."""
        medium = _curated_frame(
            [
                ("id-a", "text a", "medium"),
                ("id-b", "text b", "medium"),
            ]
        )
        engine = RecordingEngine({"id-a": 0.2})
        scores_path = tmp_path / "medium_perspective_scores.parquet"

        with pytest.raises(ValueError):
            score_medium_comments(medium, scores_path=scores_path, engine=engine)


class TestRequireAllMediumScored:
    """Tests for require_all_medium_scored()."""

    def test_raises_when_a_medium_id_has_no_score(self, tmp_path: Path) -> None:
        """Reject a scores file that does not cover every medium id."""
        medium = _curated_frame(
            [
                ("id-a", "text a", "medium"),
                ("id-b", "text b", "medium"),
            ]
        )
        scores_path = tmp_path / "medium_perspective_scores.parquet"
        _write_scores(scores_path, [("id-a", 0.2)])

        with pytest.raises(ValueError):
            require_all_medium_scored(medium, scores_path)


class TestDefaultScoreEngine:
    """Tests for default_score_engine()."""

    def test_uses_toxic_tiered_thread_pool_spec(self) -> None:
        """Build the product is_toxic_tiered thread-pool engine without labeling."""
        result = default_score_engine()

        assert result.spec.name == "is_toxic_tiered"
        assert result.spec.engine_type == "thread_pool"


class TestMainScoreFlag:
    """Tests for run.main() --score stdout."""

    def test_prints_already_and_newly_scored_counts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Report scores already on disk separately from rows scored in this run."""
        curated = _curated_frame(
            [
                ("id-a", "text a", "medium"),
                ("id-b", "text b", "medium"),
                ("id-c", "text c", "medium"),
            ]
        )
        scores_path = tmp_path / "medium_perspective_scores.parquet"
        _write_scores(scores_path, [("id-a", 0.2)])

        def fake_score(
            medium: pd.DataFrame,
            *,
            scores_path: Path,
            engine=None,
        ) -> pd.DataFrame:
            del medium, engine
            combined = _scores_frame([("id-a", 0.2), ("id-b", 0.8), ("id-c", 0.5)])
            combined.to_parquet(scores_path, index=False)
            return combined

        monkeypatch.setattr(experiment_run, "load_pinned_curated", lambda: curated)
        monkeypatch.setattr(experiment_run, "DEFAULT_SCORES_PATH", scores_path)
        monkeypatch.setattr(experiment_run, "score_medium_comments", fake_score)

        result = experiment_run.main(["--score"])
        stdout = capsys.readouterr().out

        expected = 0
        assert result == expected
        assert "medium_rows=3" in stdout
        assert "already_scored=1" in stdout
        assert "newly_scored=2" in stdout
        assert f"scores_path={scores_path}" in stdout


ORIGINAL_OBJECT_KEY = V2_OBJECT_KEY.replace("mirrorview_v2.parquet", "mirrorview.parquet")
POLITICAL_STANCE_COLUMN = "political_stance"


def _scores_with_ids(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return _scores_frame(rows)


class TestSelectPromotions:
    """Tests for select_promotions()."""

    def test_breaks_probability_ties_by_source_record_id(self) -> None:
        """Keep the smaller source_record_id when toxicity_prob ties."""
        scores = _scores_with_ids([("b", 0.9), ("a", 0.9), ("c", 0.1)])

        result = select_promotions(scores, count=2)

        expected = ["a", "b"]
        assert result == expected

    def test_ranks_by_probability_not_perspective_tier(self) -> None:
        """Ignore Perspective toxicity_tier when choosing the top id."""
        scores = pd.DataFrame(
            [
                {
                    SOURCE_RECORD_ID_COLUMN: "a",
                    TOXICITY_PROB_COLUMN: 0.1,
                    "toxicity_tier": "high",
                },
                {
                    SOURCE_RECORD_ID_COLUMN: "b",
                    TOXICITY_PROB_COLUMN: 0.9,
                    "toxicity_tier": "low",
                },
            ]
        )

        result = select_promotions(scores, count=1)

        expected = ["b"]
        assert result == expected

    def test_raises_when_fewer_rows_than_count(self) -> None:
        """Reject a scores table that cannot fill the promotion count."""
        scores = _scores_with_ids([("a", 0.9)])

        with pytest.raises(ValueError):
            select_promotions(scores, count=2)


class TestApplyPromotions:
    """Tests for apply_promotions()."""

    def test_sets_medium_promotion_rows_to_high_and_keeps_other_cells(self) -> None:
        """Change only the promoted medium tiers; keep order and other values."""
        curated = pd.DataFrame(
            [
                {
                    SOURCE_RECORD_ID_COLUMN: "keep-low",
                    TEXT_COLUMN: "civil",
                    LLM_TOXICITY_TIER_COLUMN: "low",
                    POLITICAL_STANCE_COLUMN: "left",
                },
                {
                    SOURCE_RECORD_ID_COLUMN: "promote-a",
                    TEXT_COLUMN: "rude a",
                    LLM_TOXICITY_TIER_COLUMN: "medium",
                    POLITICAL_STANCE_COLUMN: "right",
                },
                {
                    SOURCE_RECORD_ID_COLUMN: "keep-high",
                    TEXT_COLUMN: "threat",
                    LLM_TOXICITY_TIER_COLUMN: "high",
                    POLITICAL_STANCE_COLUMN: "left",
                },
                {
                    SOURCE_RECORD_ID_COLUMN: "promote-b",
                    TEXT_COLUMN: "rude b",
                    LLM_TOXICITY_TIER_COLUMN: "medium",
                    POLITICAL_STANCE_COLUMN: "left",
                },
            ]
        )
        original = curated.copy()

        result = apply_promotions(curated, ["promote-a", "promote-b"])

        expected_tiers = ["low", "high", "high", "high"]
        assert result[LLM_TOXICITY_TIER_COLUMN].tolist() == expected_tiers
        assert list(result.columns) == list(original.columns)
        assert len(result) == len(original)
        assert result[SOURCE_RECORD_ID_COLUMN].tolist() == original[SOURCE_RECORD_ID_COLUMN].tolist()
        unchanged = result.drop(columns=[LLM_TOXICITY_TIER_COLUMN])
        expected_unchanged = original.drop(columns=[LLM_TOXICITY_TIER_COLUMN])
        pd.testing.assert_frame_equal(unchanged.reset_index(drop=True), expected_unchanged)
        pd.testing.assert_frame_equal(curated, original)

    def test_raises_when_promotion_id_is_not_medium(self) -> None:
        """Reject a promotion id whose current LLM toxicity tier is low."""
        curated = _curated_frame(
            [
                ("id-low", "civil text", "low"),
                ("id-medium", "rude text", "medium"),
            ]
        )

        with pytest.raises(ValueError):
            apply_promotions(curated, ["id-low"])


class TestWriteCuratedV2:
    """Tests for write_curated_v2()."""

    def test_uploads_with_put_new_and_never_touches_the_original_key(self) -> None:
        """Call put_new on the v2 key and do not call replace or the original key."""
        curated_v2 = _curated_frame([("id-medium", "rude text", "high")])
        store = FakeStore(b"")

        result = write_curated_v2(curated_v2, store=store, key=V2_OBJECT_KEY)

        expected_key = V2_OBJECT_KEY
        assert store.put_new_calls == [expected_key]
        assert store.replace_calls == []
        assert ORIGINAL_OBJECT_KEY not in store.put_new_calls
        assert result == sha256_hex(store.put_new_bodies[0])

    def test_propagates_file_exists_error_from_put_new(self) -> None:
        """Surface FileExistsError when the v2 object already exists."""
        curated_v2 = _curated_frame([("id-medium", "rude text", "high")])
        store = FakeStore(b"", put_new_error=FileExistsError("exists"))

        with pytest.raises(FileExistsError):
            write_curated_v2(curated_v2, store=store, key=V2_OBJECT_KEY)

        assert store.replace_calls == []
