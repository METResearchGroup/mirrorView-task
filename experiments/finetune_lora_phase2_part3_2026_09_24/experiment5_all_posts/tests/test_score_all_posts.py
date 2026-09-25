"""Tests for experiment5 all-posts scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.evaluate import compute_metrics
from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
)
from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.score_all_posts import (
    build_by_remove_votes_rows,
    build_overall_rows,
    invalid_rate,
    merge_all_posts_with_predictions,
    render_results_markdown,
    score_all_models,
    score_frame,
    write_score_csvs,
)

ALL_POSTS_COLUMNS = (
    "message_id",
    "decision",
    "keep_remove_label",
    "n_raters",
    "n_remove",
    "split",
    "in_unanimous",
)
PRED_COLUMNS = (
    "message_id",
    "decision",
    "keep_remove_label",
    "raw_generation",
    "predicted_decision",
    "predicted_label",
)


def _posts_row(
    message_id: str,
    gold: int,
    split: str,
    in_unanimous: bool,
    n_raters: int,
    n_remove: int,
) -> dict[str, object]:
    decision = "remove" if gold == 1 else "keep"
    return {
        "message_id": message_id,
        "decision": decision,
        "keep_remove_label": gold,
        "n_raters": n_raters,
        "n_remove": n_remove,
        "split": split,
        "in_unanimous": in_unanimous,
    }


def _pred_row(
    message_id: str,
    gold: int,
    predicted_decision: str,
    predicted_label: object,
) -> dict[str, object]:
    decision = "remove" if gold == 1 else "keep"
    return {
        "message_id": message_id,
        "decision": decision,
        "keep_remove_label": gold,
        "raw_generation": f"raw-{message_id}",
        "predicted_decision": predicted_decision,
        "predicted_label": predicted_label,
    }


def _write_csv(path: Path, rows: list[dict[str, object]], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(columns)).to_csv(path, index=False)


class TestFourRowMetrics:
    """Hand-computed accuracy / precision / recall / F1 on four rows."""

    def test_known_metrics_match_sklearn(self, tmp_path: Path):
        posts = [
            _posts_row("m1", 1, "train", True, 5, 5),
            _posts_row("m2", 0, "test", False, 3, 0),
            _posts_row("m3", 1, "train", False, 5, 3),
            _posts_row("m4", 0, "test", True, 5, 0),
        ]
        preds = [
            _pred_row("m1", 1, "remove", 1),
            _pred_row("m2", 0, "keep", 0),
            _pred_row("m3", 1, "keep", 0),
            _pred_row("m4", 0, "remove", 1),
        ]
        posts_path = tmp_path / "all_posts.csv"
        pred_path = tmp_path / "preds.csv"
        _write_csv(posts_path, posts, ALL_POSTS_COLUMNS)
        _write_csv(pred_path, preds, PRED_COLUMNS)

        all_posts = pd.read_csv(posts_path)
        predictions = pd.read_csv(pred_path)
        merged = merge_all_posts_with_predictions(all_posts, predictions)
        metrics = score_frame(merged)

        y_true = [1, 0, 1, 0]
        y_pred = [1, 0, 0, 1]
        expected = compute_metrics(y_true, y_pred)

        assert metrics["accuracy"] == expected["accuracy"] == 0.5
        assert metrics["precision"] == expected["precision"] == 0.5
        assert metrics["recall"] == expected["recall"] == 0.5
        assert metrics["f1"] == expected["f1"] == 0.5
        assert metrics["invalid_rate"] == 0.0


class TestFiveRaterBuckets:
    """by_remove_votes uses only n_raters == 5."""

    def test_bucket_counts_and_empty_bucket_metrics(self, tmp_path: Path):
        posts = [
            _posts_row("a", 0, "train", False, 5, 0),
            _posts_row("b", 1, "train", False, 5, 5),
            _posts_row("c", 0, "test", False, 3, 0),
        ]
        preds = [
            _pred_row("a", 0, "keep", 0),
            _pred_row("b", 1, "remove", 1),
            _pred_row("c", 0, "keep", 0),
        ]
        all_posts = pd.DataFrame(posts, columns=list(ALL_POSTS_COLUMNS))
        predictions = pd.DataFrame(preds, columns=list(PRED_COLUMNS))
        merged = merge_all_posts_with_predictions(all_posts, predictions)

        rows = build_by_remove_votes_rows(merged, "modal_model")

        assert len(rows) == 6
        by_n_remove = {int(row["n_remove"]): row for row in rows}
        assert by_n_remove[0]["n"] == 1
        assert by_n_remove[0]["n_label_remove"] == 0
        assert by_n_remove[5]["n"] == 1
        assert by_n_remove[5]["n_label_remove"] == 1
        assert by_n_remove[1]["n"] == 0
        assert by_n_remove[1]["accuracy"] == 0.0
        assert by_n_remove[1]["f1"] == 0.0


class TestInvalidRate:
    """Invalid predictions affect invalid_rate and scoring."""

    def test_invalid_rate_fraction(self):
        rows = [
            _pred_row("m1", 0, "keep", 0),
            _pred_row("m2", 0, INVALID_DECISION, pd.NA),
            _pred_row("m3", 1, "remove", 1),
            _pred_row("m4", 0, "keep", pd.NA),
        ]
        frame = pd.DataFrame(rows, columns=list(PRED_COLUMNS))
        assert invalid_rate(frame) == 0.5

    def test_invalid_lowers_accuracy_in_score_frame(self):
        posts = [_posts_row("m1", 1, "train", False, 5, 1)]
        good_pred = [_pred_row("m1", 1, "remove", 1)]
        bad_pred = [_pred_row("m1", 1, INVALID_DECISION, pd.NA)]
        posts_frame = pd.DataFrame(posts, columns=list(ALL_POSTS_COLUMNS))

        good_merged = merge_all_posts_with_predictions(
            posts_frame,
            pd.DataFrame(good_pred, columns=list(PRED_COLUMNS)),
        )
        bad_merged = merge_all_posts_with_predictions(
            posts_frame,
            pd.DataFrame(bad_pred, columns=list(PRED_COLUMNS)),
        )

        good_metrics = score_frame(good_merged)
        bad_metrics = score_frame(bad_merged)

        assert good_metrics["accuracy"] == 1.0
        assert bad_metrics["accuracy"] == 0.0
        assert bad_metrics["invalid_rate"] == 1.0


class TestOverallSlices:
    """Overall rows cover slice filters."""

    def test_train_test_and_unanimous_slices(self):
        posts = [
            _posts_row("t1", 1, "train", True, 5, 5),
            _posts_row("t2", 0, "test", False, 5, 0),
            _posts_row("t3", 0, "train", False, 5, 0),
        ]
        preds = [
            _pred_row("t1", 1, "remove", 1),
            _pred_row("t2", 0, "keep", 0),
            _pred_row("t3", 0, "keep", 0),
        ]
        merged = merge_all_posts_with_predictions(
            pd.DataFrame(posts, columns=list(ALL_POSTS_COLUMNS)),
            pd.DataFrame(preds, columns=list(PRED_COLUMNS)),
        )
        rows = build_overall_rows(merged, "unanimous_model")
        lookup = {str(row["slice"]): row for row in rows}

        assert lookup["all_posts"]["n"] == 3
        assert lookup["train"]["n"] == 2
        assert lookup["test"]["n"] == 1
        assert lookup["unanimous_posts"]["n"] == 1


class TestCliOutputs:
    """End-to-end scoring writes CSVs and RESULTS.md."""

    def test_score_all_models_writes_outputs(self, tmp_path: Path):
        posts = [
            _posts_row("m1", 1, "train", True, 5, 5),
            _posts_row("m2", 0, "test", False, 5, 0),
        ]
        preds = [
            _pred_row("m1", 1, "remove", 1),
            _pred_row("m2", 0, "keep", 0),
        ]
        posts_path = tmp_path / "data" / "all_posts.csv"
        uni_preds = tmp_path / "preds" / "unanimous_model" / "all_posts.csv"
        modal_preds = tmp_path / "preds" / "modal_model" / "all_posts.csv"
        _write_csv(posts_path, posts, ALL_POSTS_COLUMNS)
        _write_csv(uni_preds, preds, PRED_COLUMNS)
        _write_csv(modal_preds, preds, PRED_COLUMNS)

        overall_rows, by_remove_rows = score_all_models(
            posts_path,
            {
                "unanimous_model": uni_preds,
                "modal_model": modal_preds,
            },
        )
        scores_dir = tmp_path / "scores"
        write_score_csvs(scores_dir, overall_rows, by_remove_rows)
        results_path = tmp_path / "RESULTS.md"
        results_path.write_text(
            render_results_markdown(overall_rows, by_remove_rows),
            encoding="utf-8",
        )

        overall = pd.read_csv(scores_dir / "overall.csv")
        by_remove = pd.read_csv(scores_dir / "by_remove_votes.csv")
        assert len(overall) == 8
        assert len(by_remove) == 12
        assert "trained on" in results_path.read_text(encoding="utf-8")
