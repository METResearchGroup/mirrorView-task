"""Tests for smoke cost scaling helpers."""

from __future__ import annotations

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA,
    MODEL_FOLDER_BEDROCK_QWEN,
    MODEL_FOLDER_OPENAI,
    CostRow,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import (
    COST_ESTIMATE_RELATIVE_PATH,
    EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH,
    ExperimentCostSection,
    MedianTokens,
    TokenUsageRecord,
    build_experiment6_cost_markdown,
    build_experiment6_cost_rows,
    build_experiment_sections,
    cost_row_for_model,
    format_cost_table,
    mean_prompt_chars,
    median_tokens,
    scale_input_tokens,
    scale_output_tokens,
    total_rows,
)


class TestMedianTokens:
    """Tests for median_tokens."""

    def test_returns_median_of_successful_requests(self):
        """Median input and output tokens use the middle successful request."""
        usages = [
            TokenUsageRecord("a", 100, 10),
            TokenUsageRecord("b", 200, 20),
            TokenUsageRecord("c", 300, 30),
        ]
        result = median_tokens(usages)
        expected = MedianTokens(input_tokens=200.0, output_tokens=20.0)
        assert result == expected


class TestScaleInputTokens:
    """Tests for scale_input_tokens."""

    def test_scales_by_user_count_and_length_ratio(self):
        """Input tokens scale with cohort size and prompt-length ratio."""
        result = scale_input_tokens(100.0, 1000, 1.5)
        expected = 150000
        assert result == expected


class TestScaleOutputTokens:
    """Tests for scale_output_tokens."""

    def test_scales_by_user_count_only(self):
        """Output tokens scale with cohort size only."""
        result = scale_output_tokens(12.5, 1000)
        expected = 12500
        assert result == expected


class TestCostRowForModel:
    """Tests for cost_row_for_model."""

    def test_applies_low_and_high_multipliers(self):
        """Low and high bounds are 0.5x and 2x the median."""
        result = cost_row_for_model(MODEL_FOLDER_OPENAI, 1_000_000, 1_000_000)
        expected_median = 0.10 * 1 + 0.625 * 1
        assert result.median_cost_usd == round(expected_median, 2)
        assert result.low_cost_usd == round(expected_median * 0.5, 2)
        assert result.high_cost_usd == round(expected_median * 2.0, 2)


class TestBuildExperimentSections:
    """Tests for build_experiment_sections."""

    def test_experiment_two_scales_input_by_prompt_length(
        self,
        sample_user,
        sample_trials,
    ):
        """Experiment 2 input tokens grow when prompts are longer than experiment 1."""
        users = (sample_user,)
        trials_by_user = {sample_user.prolific_id: sample_trials}
        medians = {
            MODEL_FOLDER_OPENAI: MedianTokens(input_tokens=100.0, output_tokens=10.0),
            MODEL_FOLDER_BEDROCK_MICRO_NOVA: MedianTokens(50.0, 5.0),
            MODEL_FOLDER_BEDROCK_QWEN: MedianTokens(50.0, 5.0),
            MODEL_FOLDER_BEDROCK_CLAUDE: MedianTokens(50.0, 5.0),
        }
        sections = build_experiment_sections(users, trials_by_user, medians)
        exp1_chars = mean_prompt_chars(users, trials_by_user, 1)
        exp2_chars = mean_prompt_chars(users, trials_by_user, 2)
        ratio = exp2_chars / exp1_chars
        expected_tokens_in = scale_input_tokens(100.0, 1, ratio)
        assert sections[1].rows[0].estimated_tokens_in == expected_tokens_in
        assert sections[0].rows[0].estimated_tokens_in == 100


class TestFormatCostTable:
    """Tests for format_cost_table."""

    def test_renders_required_columns(self):
        """Table includes the issue column set."""
        rows = (
            CostRow(
                model=MODEL_FOLDER_OPENAI,
                estimated_tokens_in=10,
                estimated_tokens_out=5,
                median_cost_usd=1.0,
                low_cost_usd=0.5,
                high_cost_usd=2.0,
            ),
        )
        result = format_cost_table(rows)
        assert "model | estimated tokens in | estimated tokens out" in result
        assert MODEL_FOLDER_OPENAI in result


class TestTotalRows:
    """Tests for total_rows."""

    def test_sums_across_experiments(self):
        """Total rows sum token and cost estimates across experiments 1-4."""
        row = CostRow(
            model=MODEL_FOLDER_OPENAI,
            estimated_tokens_in=10,
            estimated_tokens_out=5,
            median_cost_usd=1.0,
            low_cost_usd=0.5,
            high_cost_usd=2.0,
        )
        sections = tuple(
            ExperimentCostSection(experiment_number=n, rows=(row,))
            for n in range(1, 5)
        )
        result = total_rows(sections)
        assert result[0].estimated_tokens_in == 40
        assert result[0].median_cost_usd == 4.0


class TestBuildExperiment6CostRows:
    """Tests for build_experiment6_cost_rows."""

    def test_scales_median_tokens_by_pair_call_count(self):
        """Experiment 6 tokens equal per-pair medians times 19960 calls."""
        # Arrange
        medians = {
            MODEL_FOLDER_OPENAI: MedianTokens(input_tokens=100.0, output_tokens=10.0),
            MODEL_FOLDER_BEDROCK_MICRO_NOVA: MedianTokens(50.0, 5.0),
            MODEL_FOLDER_BEDROCK_QWEN: MedianTokens(80.0, 8.0),
        }
        pair_call_count = 19960

        # Act
        result = build_experiment6_cost_rows(medians, pair_call_count)

        # Assert
        assert [row.model for row in result] == [
            MODEL_FOLDER_OPENAI,
            MODEL_FOLDER_BEDROCK_MICRO_NOVA,
            MODEL_FOLDER_BEDROCK_QWEN,
        ]
        assert MODEL_FOLDER_BEDROCK_CLAUDE not in [row.model for row in result]
        assert result[0].estimated_tokens_in == 1996000
        assert result[0].estimated_tokens_out == 199600


class TestBuildExperiment6CostMarkdown:
    """Tests for build_experiment6_cost_markdown."""

    def test_omits_claude_and_parent_experiment_sections(self):
        """The experiment 6 cost file has three models and excludes Claude."""
        # Arrange
        rows = build_experiment6_cost_rows(
            {
                MODEL_FOLDER_OPENAI: MedianTokens(100.0, 10.0),
                MODEL_FOLDER_BEDROCK_MICRO_NOVA: MedianTokens(50.0, 5.0),
                MODEL_FOLDER_BEDROCK_QWEN: MedianTokens(80.0, 8.0),
            },
            19960,
        )

        # Act
        result = build_experiment6_cost_markdown(rows)

        # Assert
        assert result.startswith("# Experiment 6 cost estimate")
        assert "Claude Sonnet 4.6 is excluded from experiment 6." in result
        assert "bedrock_claude" not in result
        assert "## Experiment 1" not in result
        assert MODEL_FOLDER_OPENAI in result
        assert MODEL_FOLDER_BEDROCK_QWEN in result


class TestExperiment6CostPath:
    """Tests for the experiment 6 cost object key."""

    def test_is_not_the_parent_cost_file(self):
        """Experiment 6 writes its own COST_ESTIMATE.md under experiment6/."""
        # Arrange / Act / Assert
        assert COST_ESTIMATE_RELATIVE_PATH.endswith(
            "experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md"
        )
        assert EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH.endswith(
            "experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md"
        )
        assert EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH != COST_ESTIMATE_RELATIVE_PATH
