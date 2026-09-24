"""Tests for the LiteLLM client wrapper."""

from __future__ import annotations

import json
import signal
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from litellm.exceptions import Timeout

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client import (
    REQUEST_TIMEOUT_SECONDS,
    SpendCapExceeded,
    _litellm_completion,
    append_cost_log,
    complete_structured,
    read_cumulative_cost_usd,
)


class _ProbeModel(BaseModel):
    ok: bool


def _mock_response(raw_json: str, *, input_tokens: int, output_tokens: int, reasoning_tokens: int = 0):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=raw_json))]
    response.usage = MagicMock(
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
    )
    return response


def test_complete_structured_writes_per_call_json(tmp_path: Path) -> None:
    """complete_structured writes one JSON artifact with request, response, and usage."""
    payload = {"ok": True}
    with patch("litellm.completion", return_value=_mock_response(json.dumps(payload), input_tokens=10, output_tokens=5)):
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert {"request", "response", "usage"} <= set(data)


def test_complete_structured_appends_cost_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_structured appends one cost log line with the expected cumulative total."""
    cost_log = tmp_path / "cost_log.jsonl"
    monkeypatch.setattr(paths, "cost_log_path", lambda: cost_log)
    payload = {"ok": True}
    with patch("litellm.completion", return_value=_mock_response(json.dumps(payload), input_tokens=1000, output_tokens=200)):
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    lines = cost_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["cumulative_cost_usd"] == pytest.approx(0.0002)


def test_spend_cap_blocks_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_structured raises SpendCapExceeded when cumulative cost is at the cap."""
    cost_log = tmp_path / "cost_log.jsonl"
    cost_log.write_text(
        json.dumps({"cumulative_cost_usd": constants.SPEND_CAP_USD}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "cost_log_path", lambda: cost_log)
    with patch("litellm.completion") as mock_completion:
        with pytest.raises(SpendCapExceeded):
            complete_structured(
                [{"role": "user", "content": "hi"}],
                _ProbeModel,
                stage="discovery",
                arm="original_only",
                call_index=1,
                output_dir=tmp_path,
                run_metadata={"model": constants.LLM_MODEL_ID},
            )
    mock_completion.assert_not_called()


def test_reasoning_effort_none_passed(tmp_path: Path) -> None:
    """complete_structured passes reasoning_effort none and the LiteLLM model id."""
    payload = {"ok": True}
    with patch("litellm.completion", return_value=_mock_response(json.dumps(payload), input_tokens=10, output_tokens=5)) as mock_completion:
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    kwargs = mock_completion.call_args.kwargs
    assert kwargs["model"] == constants.LLM_LITELLM_MODEL_ID
    assert kwargs["reasoning_effort"] == constants.LLM_REASONING_EFFORT


def test_timeout_passthrough(tmp_path: Path) -> None:
    """complete_structured passes a 180 second timeout to litellm.completion."""
    payload = {"ok": True}
    with patch(
        "litellm.completion",
        return_value=_mock_response(json.dumps(payload), input_tokens=10, output_tokens=5),
    ) as mock_completion:
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    assert mock_completion.call_args.kwargs["timeout"] == float(REQUEST_TIMEOUT_SECONDS)


def test_hard_timeout_via_mock_alarm() -> None:
    """The alarm wrapper surfaces TimeoutError when SIGALRM fires during the call."""

    def hang(*args, **kwargs):
        while True:
            time.sleep(0.05)

    def fire_alarm_immediately(seconds: int) -> int:
        if seconds:
            signal.raise_signal(signal.SIGALRM)
        return 0

    with patch("litellm.completion", side_effect=hang):
        with patch("signal.alarm", side_effect=fire_alarm_immediately):
            with pytest.raises(TimeoutError):
                _litellm_completion([{"role": "user", "content": "hi"}], _ProbeModel)


def test_builtin_timeout_error_retries_once(tmp_path: Path) -> None:
    """complete_structured retries once after a SIGALRM TimeoutError."""
    payload = {"ok": True}
    with patch(
        "litellm.completion",
        side_effect=[
            TimeoutError("litellm completion exceeded 180s"),
            _mock_response(json.dumps(payload), input_tokens=10, output_tokens=5),
        ],
    ) as mock_completion:
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    assert mock_completion.call_count == 2


def test_transient_error_retries_once(tmp_path: Path) -> None:
    """complete_structured retries once after a transient LiteLLM timeout."""
    payload = {"ok": True}
    with patch(
        "litellm.completion",
        side_effect=[
            Timeout("request timed out", model=constants.LLM_LITELLM_MODEL_ID, llm_provider="openai"),
            _mock_response(json.dumps(payload), input_tokens=10, output_tokens=5),
        ],
    ) as mock_completion:
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    assert mock_completion.call_count == 2


def test_metadata_reasoning_tokens_zero(tmp_path: Path) -> None:
    """Per-call usage records zero reasoning tokens from the mock response."""
    payload = {"ok": True}
    with patch("litellm.completion", return_value=_mock_response(json.dumps(payload), input_tokens=10, output_tokens=5, reasoning_tokens=0)):
        complete_structured(
            [{"role": "user", "content": "hi"}],
            _ProbeModel,
            stage="discovery",
            arm="original_only",
            call_index=1,
            output_dir=tmp_path,
            run_metadata={"model": constants.LLM_MODEL_ID},
        )
    artifact = next(tmp_path.glob("*.json"))
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["usage"]["reasoning_tokens"] == 0
