"""Tests for experiment 5 error analysis helpers."""

from __future__ import annotations

from experiments.ai_simulation_responses_2026_09_11.shared.constants import CohortUser
from experiments.ai_simulation_responses_2026_09_11.shared.error_analysis import (
    ScoredCell,
    rank_false_negative_posts,
    rank_worst_users,
)


def _user(prolific_id: str) -> CohortUser:
    return CohortUser(
        prolific_id=prolific_id,
        participant_id=f"pid-{prolific_id}",
        source_file_epoch_ms=1,
        party_group="democrat",
        age="30",
        gender="woman",
        education="bachelors",
        political_affiliation="democrat",
        party_lean="democrat",
        political_ideology="3",
        political_follow="5",
        rep_id="2",
        dem_id="6",
        attitude_reduce_abortion="50",
        attitude_citizenship_undocumented="50",
        attitude_restrict_guns="50",
        attitude_regulate_environment="50",
        attitude_raise_wealth_taxes="50",
        attitude_expand_medicaid="50",
        phase1_pair_reflection_text="reflection",
        phase1_pair_influence_rating=4,
    )


def _cell(
    *,
    prolific_id: str,
    post_id: str,
    gold: int,
    pred: int,
    experiment_number: int = 1,
    model: str = "openai",
    pair_index: int = 1,
) -> ScoredCell:
    return ScoredCell(
        experiment_number=experiment_number,
        model=model,
        prolific_id=prolific_id,
        pair_index=pair_index,
        post_id=post_id,
        gold=gold,
        pred=pred,
        sampled_stance="left",
        sample_toxicity_type="sample_low_toxicity",
    )


class TestRankFalseNegativePosts:
    """Tests for rank_false_negative_posts."""

    def test_higher_false_negative_rate_ranks_first(self):
        """Post A ranks above post B when A is always a false negative."""
        # Arrange
        models = ("openai", "bedrock_micro_nova", "bedrock_qwen", "bedrock_claude")
        cells = []
        for experiment_number in (1, 2, 3, 4):
            for model in models:
                cells.append(
                    _cell(
                        prolific_id="user-a",
                        post_id="post-a",
                        gold=1,
                        pred=0,
                        experiment_number=experiment_number,
                        model=model,
                    )
                )
                cells.append(
                    _cell(
                        prolific_id="user-b",
                        post_id="post-b",
                        gold=1,
                        pred=1,
                        experiment_number=experiment_number,
                        model=model,
                    )
                )

        # Act
        ranked, shortfall = rank_false_negative_posts(cells, k=2)

        # Assert
        assert len(ranked) == 1
        assert ranked[0].post_id == "post-a"
        assert ranked[0].error_rate == 1.0
        assert shortfall == 1


class TestRankWorstUsers:
    """Tests for rank_worst_users."""

    def test_returns_lowest_f1_users_in_order(self):
        """The k lowest mean-F1 users are returned in increasing F1 order."""
        # Arrange
        users = {f"user-{index}": _user(f"user-{index}") for index in range(10)}
        cells: list[ScoredCell] = []
        for index in range(10):
            prolific_id = f"user-{index}"
            correct_pairs = index * 2
            for pair_index in range(1, 21):
                gold = 1
                pred = 1 if pair_index <= correct_pairs else 0
                for experiment_number in (1, 2, 3, 4):
                    cells.append(
                        _cell(
                            prolific_id=prolific_id,
                            post_id=f"post-{pair_index}",
                            gold=gold,
                            pred=pred,
                            experiment_number=experiment_number,
                            model="openai",
                            pair_index=pair_index,
                        )
                    )

        # Act
        ranked, shortfall = rank_worst_users(cells, users, k=3)

        # Assert
        assert shortfall == 0
        assert [row.prolific_id for row in ranked] == ["user-0", "user-1", "user-2"]
        assert ranked[0].mean_f1 <= ranked[1].mean_f1 <= ranked[2].mean_f1
