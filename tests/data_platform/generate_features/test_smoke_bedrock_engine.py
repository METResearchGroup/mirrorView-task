"""Tests for Bedrock Converse engine smoke-test helpers."""

from __future__ import annotations

import pytest

from data_platform.generate_features.engines.bedrock_engine import BedrockUsage
from data_platform.generate_features.smoke_bedrock_engine import (
    BedrockEngineSmokeMetrics,
    ON_DEMAND_INPUT_USD_PER_MILLION,
    ON_DEMAND_OUTPUT_USD_PER_MILLION,
    TOKENS_PER_MILLION,
    compute_bedrock_engine_smoke_metrics,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO


class TestComputeBedrockEngineSmokeMetrics:
    """Tests for compute_bedrock_engine_smoke_metrics()."""

    def test_reports_throughput_tokens_and_cost(self) -> None:
        usage = BedrockUsage(input_tokens=1000, output_tokens=50, total_tokens=1050)

        result = compute_bedrock_engine_smoke_metrics(
            usage,
            10,
            2.0,
            10,
            DEFAULT_BEDROCK_NOVA_MICRO,
        )
        expected = BedrockEngineSmokeMetrics(
            post_count=10,
            labeled_count=10,
            elapsed_seconds=2.0,
            posts_per_second=5.0,
            tokens_per_second=525.0,
            estimated_input_tokens_per_request=100.0,
            estimated_output_tokens_per_request=5.0,
            prompt_tokens=1000,
            completion_tokens=50,
            total_tokens=1050,
            model=DEFAULT_BEDROCK_NOVA_MICRO,
            estimated_cost_usd=(
                1000 * ON_DEMAND_INPUT_USD_PER_MILLION
                + 50 * ON_DEMAND_OUTPUT_USD_PER_MILLION
            )
            / TOKENS_PER_MILLION,
        )

        assert result == expected

    def test_raises_when_elapsed_time_is_not_positive(self) -> None:
        usage = BedrockUsage(10, 2, 12)

        with pytest.raises(ValueError, match="elapsed"):
            compute_bedrock_engine_smoke_metrics(
                usage, 1, 0.0, 1, DEFAULT_BEDROCK_NOVA_MICRO
            )

    def test_raises_when_request_count_is_zero(self) -> None:
        usage = BedrockUsage(0, 0, 0)

        with pytest.raises(ValueError, match="request_count"):
            compute_bedrock_engine_smoke_metrics(
                usage, 0, 1.0, 0, DEFAULT_BEDROCK_NOVA_MICRO
            )
