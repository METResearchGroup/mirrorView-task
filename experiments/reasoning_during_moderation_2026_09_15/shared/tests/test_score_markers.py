"""Tests for score_trace() and paired_arm_comparison()."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment4.markers import (
    density_per_thousand,
    score_trace,
    score_trace_phrase,
    score_trace_strict,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment4.run import (
    EMPTY_GPU_CLOSER,
    HIGH_ITEM_RATE,
    PENDING_EXP2_CLOSER,
    _phrase_finding,
    _pooled_high_items,
    _strict_finding,
    _token_finding,
    results_closer,
    trace_jsonl_path,
    traces_are_complete,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment4.summarize import (
    group_contrasts,
    marker_item_rates,
    marker_rates,
    paired_arm_comparison,
    phrase_marker_rates,
    strict_marker_rates,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    PROMPT_ARM_CRITERIA,
    PROMPT_ARM_STUDY,
    QWEN_MODEL_ID,
    STATUS_VALID,
    VLLM_OUTPUT_DIRNAME,
)

MARKED_TEXT = "I am not sure. wait, the posts conflict."
CLEAN_TEXT = "Allow both."
MAYBE_ORIGINAL_TEXT = "maybe the original is fine"
HOWEVER_TEXT = "however the posts are similar"
BOTH_POSTS_TEXT = "both posts should stay up"
WAIT_TEXT = "wait that changes the call"
BORDERLINE_TEXT = "this is borderline"
EXP1_COUNT = 10
EXP2_COUNT = 8
EXPECTED_TOKEN_DIFF = -2.0
DENSITY_HITS = 2
DENSITY_TOKENS = 1000
EXPECTED_DENSITY = 2.0
POOLED_N = 10
POOLED_HIGH_RATE = 1.0
POOLED_ZERO_RATE = 0.0
POOLED_LOW_RATE = 0.04
EXPECTED_POOLED_RATE = 0.5
TOKEN_SPLIT_MEAN = 3081.0
TOKEN_KEEP_MEAN = 3093.0
TOKEN_REMOVE_MEAN = 2676.0
N_SPLIT = 2201
N_KEEP = 2260
N_REMOVE = 214


class TestScoreTrace:
    """Tests for score_trace function."""

    def test_flags_uncertainty_revision_and_tension(self) -> None:
        """Verifies all three families fire on the confirmed mixed sentence."""
        result = score_trace(MARKED_TEXT)

        assert result.uncertainty is True
        assert result.revision is True
        assert result.tension is True

    def test_clean_text_has_no_flags(self) -> None:
        """Verifies a short allow sentence scores false on every family."""
        result = score_trace(CLEAN_TEXT)

        assert result.uncertainty is False
        assert result.revision is False
        assert result.tension is False

    def test_maybe_token_and_dropped_original(self) -> None:
        """Verifies maybe is an uncertainty token and original is not tension."""
        result = score_trace(MAYBE_ORIGINAL_TEXT)

        assert result.uncertainty is True
        assert result.tension is False


class TestScoreTraceStrict:
    """Tests for score_trace_strict versus broad flags."""

    def test_however_is_broad_not_strict(self) -> None:
        """Verifies however flags broad uncertainty and not strict uncertainty."""
        broad = score_trace(HOWEVER_TEXT)
        strict = score_trace_strict(HOWEVER_TEXT)

        assert broad.uncertainty is True
        assert strict.uncertainty is False

    def test_both_posts_is_broad_not_strict_tension(self) -> None:
        """Verifies both posts flags broad tension and not strict tension."""
        broad = score_trace(BOTH_POSTS_TEXT)
        strict = score_trace_strict(BOTH_POSTS_TEXT)

        assert broad.tension is True
        assert strict.tension is False

    def test_wait_is_broad_not_strict_revision(self) -> None:
        """Verifies wait flags broad revision and not strict revision."""
        broad = score_trace(WAIT_TEXT)
        strict = score_trace_strict(WAIT_TEXT)

        assert broad.revision is True
        assert strict.revision is False

    def test_borderline_stays_strict_uncertainty(self) -> None:
        """Verifies borderline remains uncertainty on the strict list."""
        broad = score_trace(BORDERLINE_TEXT)
        strict = score_trace_strict(BORDERLINE_TEXT)

        assert broad.uncertainty is True
        assert strict.uncertainty is True


class TestScoreTracePhrase:
    """Tests for phrase-only family flags."""

    def test_however_is_not_phrase_uncertainty(self) -> None:
        """Verifies a discourse token does not fire phrase-only uncertainty."""
        result = score_trace_phrase(HOWEVER_TEXT)

        assert result.uncertainty is False

    def test_not_sure_is_phrase_uncertainty(self) -> None:
        """Verifies the confirmed not sure phrase still flags phrase uncertainty."""
        result = score_trace_phrase(MARKED_TEXT)

        assert result.uncertainty is True


class TestDensityPerThousand:
    """Tests for density_per_thousand."""

    def test_two_hits_per_thousand_tokens(self) -> None:
        """Verifies two distinct hits on 1000 tokens equal density 2."""
        result = density_per_thousand(DENSITY_HITS, DENSITY_TOKENS)

        assert result == EXPECTED_DENSITY

    def test_zero_tokens_returns_zero(self) -> None:
        """Verifies a zero-length span does not divide by zero."""
        result = density_per_thousand(DENSITY_HITS, 0)

        assert result == 0.0


class TestPairedArmComparison:
    """Tests for paired_arm_comparison function."""

    def test_mean_thinking_token_difference(self) -> None:
        """Verifies experiment 2 minus experiment 1 mean token difference."""
        exp1 = _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT)
        exp2 = _trace_row(PROMPT_ARM_CRITERIA, EXP2_COUNT)

        result = paired_arm_comparison(exp1, exp2)
        row = result.iloc[0]

        assert float(row["mean_thinking_token_diff"]) == EXPECTED_TOKEN_DIFF


class TestStrictAndPhraseRates:
    """Tests for strict and phrase rate tables."""

    def test_however_row_drops_on_strict_uncertainty(self) -> None:
        """Verifies a however-only span has broad rate 1 and strict rate 0."""
        traces = _trace_row(PROMPT_ARM_STUDY, DENSITY_TOKENS, HOWEVER_TEXT)

        broad = marker_rates(traces)
        strict = strict_marker_rates(traces)

        assert float(broad.iloc[0]["uncertainty_rate"]) == 1.0
        assert float(strict.iloc[0]["uncertainty_rate"]) == 0.0

    def test_borderline_row_keeps_strict_uncertainty(self) -> None:
        """Verifies a borderline span has strict uncertainty rate 1."""
        traces = _trace_row(PROMPT_ARM_STUDY, DENSITY_TOKENS, BORDERLINE_TEXT)

        strict = strict_marker_rates(traces)

        assert float(strict.iloc[0]["uncertainty_rate"]) == 1.0
        assert float(strict.iloc[0]["uncertainty_density"]) == 1.0

    def test_phrase_rates_keep_not_sure_and_drop_however(self) -> None:
        """Verifies phrase-only rates follow phrases rather than tokens."""
        sure = phrase_marker_rates(
            _trace_row(PROMPT_ARM_STUDY, DENSITY_TOKENS, MARKED_TEXT)
        )
        however = phrase_marker_rates(
            _trace_row(PROMPT_ARM_STUDY, DENSITY_TOKENS, HOWEVER_TEXT)
        )

        assert float(sure.iloc[0]["uncertainty_rate"]) == 1.0
        assert float(however.iloc[0]["uncertainty_rate"]) == 0.0

    def test_item_rates_include_zero_and_however(self) -> None:
        """Verifies however is present and unused tokens still appear at rate 0."""
        traces = _trace_row(PROMPT_ARM_STUDY, DENSITY_TOKENS, HOWEVER_TEXT)

        items = marker_item_rates(traces)
        however = items[
            (items["family"] == "uncertainty")
            & (items["kind"] == "token")
            & (items["item"] == "however")
        ]
        maybe = items[
            (items["family"] == "uncertainty")
            & (items["kind"] == "token")
            & (items["item"] == "maybe")
        ]

        assert float(however.iloc[0]["rate"]) == 1.0
        assert float(maybe.iloc[0]["rate"]) == 0.0


class TestGroupContrasts:
    """Tests for group_contrasts on strict rates."""

    def test_split_minus_keep_uncertainty_rate(self) -> None:
        """Verifies split minus keep is 1 when only split has strict uncertainty."""
        traces = pd.concat(
            [
                _trace_row(
                    PROMPT_ARM_STUDY,
                    DENSITY_TOKENS,
                    BORDERLINE_TEXT,
                    group=GROUP_SPLIT,
                    post_id="s",
                ),
                _trace_row(
                    PROMPT_ARM_STUDY,
                    DENSITY_TOKENS,
                    CLEAN_TEXT,
                    group=GROUP_UNANIMOUS_KEEP,
                    post_id="k",
                ),
                _trace_row(
                    PROMPT_ARM_STUDY,
                    DENSITY_TOKENS,
                    CLEAN_TEXT,
                    group=GROUP_UNANIMOUS_REMOVE,
                    post_id="r",
                ),
            ],
            ignore_index=True,
        )
        strict = strict_marker_rates(traces)

        result = group_contrasts(strict)
        row = result[
            (result["family"] == "uncertainty") & (result["metric"] == "rate")
        ].iloc[0]

        assert float(row["split_minus_keep"]) == 1.0
        assert float(row["split"]) == 1.0
        assert float(row["keep"]) == 0.0


class TestTraceJsonlPath:
    """Tests for vLLM trace path resolution."""

    def test_qwen_path_uses_vllm_subdir(self) -> None:
        """Verifies Qwen traces resolve under outputs/vllm, not Transformers leftovers."""
        output_dir = Path("experiment1") / "outputs"
        path = trace_jsonl_path(output_dir, QWEN_MODEL_ID)

        assert path == output_dir / VLLM_OUTPUT_DIRNAME / "traces_qwen.jsonl"

    def test_deepseek_path_uses_vllm_subdir(self) -> None:
        """Verifies DeepSeek traces resolve under outputs/vllm."""
        output_dir = Path("experiment2") / "outputs"
        path = trace_jsonl_path(output_dir, DEEPSEEK_MODEL_ID)

        assert path == output_dir / VLLM_OUTPUT_DIRNAME / "traces_deepseek.jsonl"


class TestTracesAreComplete:
    """Tests for traces_are_complete."""

    def test_true_when_both_models_meet_expected_posts(self) -> None:
        """Verifies completeness when each model has two unique posts."""
        traces = pd.concat(
            [
                _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT, post_id="a"),
                _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT, post_id="b"),
                _trace_row(
                    PROMPT_ARM_STUDY,
                    EXP1_COUNT,
                    post_id="a",
                    model_id=DEEPSEEK_MODEL_ID,
                ),
                _trace_row(
                    PROMPT_ARM_STUDY,
                    EXP1_COUNT,
                    post_id="b",
                    model_id=DEEPSEEK_MODEL_ID,
                ),
            ],
            ignore_index=True,
        )

        assert traces_are_complete(traces, 2) is True

    def test_false_when_one_model_is_short(self) -> None:
        """Verifies incompleteness when DeepSeek has fewer unique posts."""
        traces = pd.concat(
            [
                _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT, post_id="a"),
                _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT, post_id="b"),
                _trace_row(
                    PROMPT_ARM_STUDY,
                    EXP1_COUNT,
                    post_id="a",
                    model_id=DEEPSEEK_MODEL_ID,
                ),
            ],
            ignore_index=True,
        )

        assert traces_are_complete(traces, 2) is False


class TestResultsCloser:
    """Tests for the RESULTS.md closing paragraph."""

    def test_pending_exp2_when_rates_exist(self) -> None:
        """Verifies experiment 1 marker rates do not claim traces were missing."""
        rates = pd.DataFrame([{"n_valid": 1}])
        comparison = pd.DataFrame()

        assert results_closer(rates, comparison) == PENDING_EXP2_CLOSER

    def test_empty_gpu_when_no_rates(self) -> None:
        """Verifies the no-trace closer when both tables are empty."""
        assert results_closer(pd.DataFrame(), pd.DataFrame()) == EMPTY_GPU_CLOSER


class TestFindings:
    """Tests for RESULTS finding paragraphs."""

    def test_token_finding_says_split_is_not_higher(self) -> None:
        """Verifies the length finding names keep as longest and remove as shortest."""
        exp1 = pd.DataFrame(
            [
                {
                    "model_id": QWEN_MODEL_ID,
                    "group": GROUP_SPLIT,
                    "mean": TOKEN_SPLIT_MEAN,
                    "n_valid": N_SPLIT,
                },
                {
                    "model_id": QWEN_MODEL_ID,
                    "group": GROUP_UNANIMOUS_KEEP,
                    "mean": TOKEN_KEEP_MEAN,
                    "n_valid": N_KEEP,
                },
                {
                    "model_id": QWEN_MODEL_ID,
                    "group": GROUP_UNANIMOUS_REMOVE,
                    "mean": TOKEN_REMOVE_MEAN,
                    "n_valid": N_REMOVE,
                },
            ]
        )

        result = _token_finding(exp1)

        assert "do not have a higher mean thinking-token count" in result
        assert "longest group is unanimous_keep" in result
        assert "shortest is unanimous_remove" in result

    def test_strict_finding_includes_split_minus_keep(self) -> None:
        """Verifies the strict finding quotes the split minus keep uncertainty gap."""
        strict = pd.DataFrame(
            [
                _strict_summary_row(GROUP_SPLIT, 0.536),
                _strict_summary_row(GROUP_UNANIMOUS_KEEP, 0.472),
                _strict_summary_row(GROUP_UNANIMOUS_REMOVE, 0.486),
            ]
        )

        result = _strict_finding(strict)

        assert "0.536 on split" in result
        assert "split minus keep +0.064" in result

    def test_phrase_finding_includes_phrase_only_uncertainty(self) -> None:
        """Verifies the phrase finding reports phrase-only uncertainty rates."""
        phrases = pd.DataFrame(
            [
                _phrase_summary_row(GROUP_SPLIT, 0.070),
                _phrase_summary_row(GROUP_UNANIMOUS_KEEP, 0.094),
                _phrase_summary_row(GROUP_UNANIMOUS_REMOVE, 0.019),
            ]
        )

        result = _phrase_finding(phrases)

        assert "phrase-only uncertainty is 0.070 on split" in result
        assert "0.094 on keep" in result


class TestPooledHighItems:
    """Tests for _pooled_high_items."""

    def test_pools_groups_and_drops_low_rates(self) -> None:
        """Verifies pooled 0.5 is kept and pooled 0.04 is dropped."""
        items = pd.DataFrame(
            [
                _item_row("borderline", GROUP_SPLIT, POOLED_HIGH_RATE),
                _item_row("borderline", GROUP_UNANIMOUS_KEEP, POOLED_ZERO_RATE),
                _item_row("maybe", GROUP_SPLIT, POOLED_LOW_RATE),
                _item_row("maybe", GROUP_UNANIMOUS_KEEP, POOLED_LOW_RATE),
            ]
        )

        result = _pooled_high_items(items)
        names = result["item"].tolist()

        assert "borderline" in names
        assert "maybe" not in names
        assert float(result.iloc[0]["rate"]) == EXPECTED_POOLED_RATE
        assert HIGH_ITEM_RATE == 0.05


def _trace_row(
    prompt_arm: str,
    count: int,
    thinking_text: str = CLEAN_TEXT,
    group: str = GROUP_SPLIT,
    post_id: str = "p1",
    model_id: str = QWEN_MODEL_ID,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "post_id": post_id,
                "model_id": model_id,
                "group": group,
                "status": STATUS_VALID,
                "prompt_arm": prompt_arm,
                "thinking_token_count": count,
                "thinking_text": thinking_text,
            }
        ]
    )


def _strict_summary_row(group: str, uncertainty_rate: float) -> dict[str, object]:
    return {
        "prompt_arm": PROMPT_ARM_STUDY,
        "model_id": QWEN_MODEL_ID,
        "group": group,
        "n_valid": 1,
        "uncertainty_rate": uncertainty_rate,
        "revision_rate": 0.0,
        "tension_rate": 0.0,
        "uncertainty_density": 0.2,
        "revision_density": 0.0,
        "tension_density": 0.0,
    }


def _phrase_summary_row(group: str, uncertainty_rate: float) -> dict[str, object]:
    return {
        "prompt_arm": PROMPT_ARM_STUDY,
        "model_id": QWEN_MODEL_ID,
        "group": group,
        "n_valid": 1,
        "uncertainty_rate": uncertainty_rate,
        "revision_rate": 0.0,
        "tension_rate": 0.9,
    }


def _item_row(item: str, group: str, rate: float) -> dict[str, object]:
    return {
        "prompt_arm": PROMPT_ARM_STUDY,
        "model_id": QWEN_MODEL_ID,
        "group": group,
        "family": "uncertainty",
        "kind": "token",
        "item": item,
        "n_valid": POOLED_N,
        "rate": rate,
    }
