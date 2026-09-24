"""Tests for post-level split and balanced CSV writers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.finetune_lora_phase2_part3_2026_09_24.shared.build_splits import (
    RANDOM_SEED,
    TRAIN_FRACTION,
    balance_split_posts,
    build_and_write_splits,
    post_level_split,
    sample_experiment_three_train,
)


def _modal_row(message_id: str, decision: str) -> dict:
    return {
        "message_id": message_id,
        "original_text": f"original-{message_id}",
        "mirror_text": f"mirror-{message_id}",
        "decision": decision,
        "keep_remove_label": 1 if decision == "remove" else 0,
        "n_raters": 3,
    }


def _tiny_modal_frame() -> pd.DataFrame:
    rows = []
    for idx in range(8):
        decision = "keep" if idx < 6 else "remove"
        rows.append(_modal_row(f"modal-{idx}", decision))
    return pd.DataFrame(rows)


def _tiny_unanimous_frame() -> pd.DataFrame:
    rows = [
        _modal_row("modal-0", "keep"),
        _modal_row("modal-1", "keep"),
        _modal_row("modal-3", "keep"),
        _modal_row("modal-5", "keep"),
        _modal_row("modal-6", "remove"),
        _modal_row("modal-7", "remove"),
    ]
    return pd.DataFrame(rows)


class TestPostLevelSplit:
    """Tests for post_level_split."""

    def test_manifest_has_one_row_per_modal_post(self):
        """Manifest covers every modal post with stratified train counts."""
        modal_df = _tiny_modal_frame()
        unanimous_ids = {"modal-0", "modal-1", "modal-6", "modal-7"}

        result = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )

        assert len(result) == len(modal_df)
        assert set(result["post_id"]) == set(modal_df["message_id"])
        keep_rows = result[result["modal_label"] == "keep"]
        remove_rows = result[result["modal_label"] == "remove"]
        assert (keep_rows["split"] == "train").sum() == int(0.8 * len(keep_rows))
        assert (remove_rows["split"] == "train").sum() == int(0.8 * len(remove_rows))

    def test_in_unanimous_true_only_for_unanimous_posts(self):
        """in_unanimous is true only when the post is in the unanimous set."""
        modal_df = _tiny_modal_frame()
        unanimous_ids = {"modal-0", "modal-6"}

        result = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )

        unanimous_mask = result["post_id"].isin(unanimous_ids)
        assert result.loc[unanimous_mask, "in_unanimous"].all()
        assert not result.loc[~unanimous_mask, "in_unanimous"].any()


class TestBalanceOutputs:
    """Tests for balanced CSV outputs."""

    def test_balanced_outputs_have_equal_keep_and_remove(self):
        """Each balanced split has equal keep and remove counts."""
        modal_df = _tiny_modal_frame()
        unanimous_df = _tiny_unanimous_frame()
        unanimous_ids = set(unanimous_df["message_id"])
        manifest = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )
        train_ids = set(manifest.loc[manifest["split"] == "train", "post_id"])
        test_ids = set(manifest.loc[manifest["split"] == "test", "post_id"])

        exp1_train = balance_split_posts(unanimous_df, train_ids, seed=RANDOM_SEED)
        exp2_train = balance_split_posts(modal_df, train_ids, seed=RANDOM_SEED)
        test_unanimous = balance_split_posts(unanimous_df, test_ids, seed=RANDOM_SEED)
        test_modal = balance_split_posts(modal_df, test_ids, seed=RANDOM_SEED)

        for frame in (exp1_train, exp2_train, test_unanimous, test_modal):
            decisions = frame["decision"].astype(str).str.lower().str.strip()
            n_keep = int((decisions == "keep").sum())
            n_remove = int((decisions == "remove").sum())
            assert n_keep == n_remove

    def test_exp1_and_exp3_train_rows_match(self, tmp_path: Path):
        """Experiment 1 and 3 train row counts and remove counts match."""
        modal_df = _tiny_modal_frame()
        unanimous_df = _tiny_unanimous_frame()
        unanimous_ids = set(unanimous_df["message_id"])
        manifest = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )
        train_ids = set(manifest.loc[manifest["split"] == "train", "post_id"])
        exp1_train = balance_split_posts(unanimous_df, train_ids, seed=RANDOM_SEED)
        exp2_train = balance_split_posts(modal_df, train_ids, seed=RANDOM_SEED)
        exp3_train = sample_experiment_three_train(
            exp2_train,
            exp1_train,
            seed=RANDOM_SEED,
        )

        assert len(exp1_train) == len(exp3_train)
        exp1_remove = int((exp1_train["decision"].str.lower() == "remove").sum())
        exp3_remove = int((exp3_train["decision"].str.lower() == "remove").sum())
        assert exp1_remove == exp3_remove


class TestLeakage:
    """Tests for train/test leakage."""

    def test_no_test_post_in_chat_train_jsonl(self, tmp_path: Path):
        """No test post id appears in any chat_train.jsonl."""
        with patch(
            "experiments.finetune_lora_phase2_part3_2026_09_24.shared.build_splits.load_dataset"
        ) as mock_load:
            mock_load.side_effect = [_tiny_modal_frame(), _tiny_unanimous_frame()]
            build_and_write_splits(force=True, seed=RANDOM_SEED)

        from experiments.finetune_lora_phase2_part3_2026_09_24.shared.create_chat_dataset import (
            create_chat_datasets,
        )

        create_chat_datasets(force=True)

        experiment_root = Path(
            "experiments/finetune_lora_phase2_part3_2026_09_24"
        )
        manifest = pd.read_csv(experiment_root / "data" / "split_manifest.csv")
        test_ids = set(manifest.loc[manifest["split"] == "test", "post_id"])

        chat_paths = [
            experiment_root / "experiment1_unanimous/data/chat_train.jsonl",
            experiment_root / "experiment2_modal/data/chat_train.jsonl",
            experiment_root / "experiment3_modal_size_matched/data/chat_train.jsonl",
        ]
        for chat_path in chat_paths:
            with chat_path.open(encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    assert record["message_id"] not in test_ids

    def test_unanimous_test_ids_subset_of_modal_test_ids(self):
        """Unanimous test post ids are a subset of modal test post ids."""
        modal_df = _tiny_modal_frame()
        unanimous_ids = set(_tiny_unanimous_frame()["message_id"])
        manifest = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )
        modal_test_ids = set(
            manifest.loc[manifest["split"] == "test", "post_id"]
        )
        unanimous_test_ids = set(
            manifest.loc[
                (manifest["split"] == "test") & manifest["in_unanimous"],
                "post_id",
            ]
        )
        assert unanimous_test_ids - modal_test_ids == set()


class TestExperimentThreeSizeMatch:
    """Tests for Experiment 3 size matching."""

    def test_sample_matches_exp1_counts(self):
        """Experiment 3 matches Experiment 1 remove and total row counts."""
        modal_df = _tiny_modal_frame()
        unanimous_df = _tiny_unanimous_frame()
        unanimous_ids = set(unanimous_df["message_id"])
        manifest = post_level_split(
            modal_df,
            unanimous_ids,
            train_fraction=TRAIN_FRACTION,
            seed=RANDOM_SEED,
        )
        train_ids = set(manifest.loc[manifest["split"] == "train", "post_id"])
        exp1_train = balance_split_posts(unanimous_df, train_ids, seed=RANDOM_SEED)
        exp2_train = balance_split_posts(modal_df, train_ids, seed=RANDOM_SEED)
        exp3_train = sample_experiment_three_train(
            exp2_train,
            exp1_train,
            seed=RANDOM_SEED,
        )

        assert len(exp3_train) == len(exp1_train)
        exp1_remove = int((exp1_train["decision"].str.lower() == "remove").sum())
        exp3_remove = int((exp3_train["decision"].str.lower() == "remove").sum())
        assert exp3_remove == exp1_remove
