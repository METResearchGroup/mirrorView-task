"""Concurrent synchronous OpenAI chat completions for Study 2 LLM steps."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from data_platform.generate_features.models import LabelTask
from openai import OpenAI
from pydantic import BaseModel

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    LLM_CONCURRENCY,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.secrets import (
    ensure_openai_api_key,
)
from lib.timestamp_utils import get_current_timestamp


@dataclass(frozen=True)
class RequestUsage:
    """Token usage for one labeled record."""

    source_record_id: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ConcurrentRun:
    """Rows, per-request usage, and wall time for one concurrent labeling run."""

    rows: list[dict]
    usage: list[RequestUsage]
    wall_seconds: float


def complete_one(
    client: OpenAI,
    task: LabelTask,
    output_schema: type[BaseModel],
    row_model: type[BaseModel],
    system_prompt: str,
    label_timestamp: str,
) -> tuple[dict, RequestUsage]:
    """Run one synchronous structured chat completion for a label task.

    Parameters
    ----------
    client
        OpenAI SDK client.
    task
        Label task with ``uri`` and user ``text``.
    output_schema
        Pydantic model passed as ``response_format``.
    row_model
        Pydantic model used to validate the saved row.
    system_prompt
        System message content.
    label_timestamp
        Shared timestamp for all rows in the run.

    Returns
    -------
    tuple[dict, RequestUsage]
        Validated row dict and token usage for the task.

    Raises
    ------
    ValueError
        When the parsed object or usage is missing.
    """
    response = client.chat.completions.parse(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        response_format=output_schema,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.text},
        ],
    )
    choice = response.choices[0].message
    parsed = choice.parsed
    if parsed is None:
        raise ValueError(f"missing parsed output for {task.uri}")
    usage = response.usage
    if usage is None:
        raise ValueError(f"missing usage for {task.uri}")
    row = {
        "source_record_id": task.uri,
        "label_timestamp": label_timestamp,
        **parsed.model_dump(),
    }
    row_model.model_validate(row)
    request_usage = RequestUsage(
        source_record_id=task.uri,
        input_tokens=int(usage.prompt_tokens),
        output_tokens=int(usage.completion_tokens),
    )
    return row, request_usage


def run_concurrent(
    tasks: list[LabelTask],
    output_schema: type[BaseModel],
    row_model: type[BaseModel],
    system_prompt: str,
    clock: Callable[[], float],
) -> ConcurrentRun:
    """Label tasks with at most ``LLM_CONCURRENCY`` synchronous API calls in flight.

    Parameters
    ----------
    tasks
        Label tasks in submission order.
    output_schema
        Structured output schema for completions.
    row_model
        Row model for on-disk validation.
    system_prompt
        System message shared by every task.
    clock
        Callable returning seconds for wall-time measurement.

    Returns
    -------
    ConcurrentRun
        Rows and usage in task order, plus elapsed wall seconds.

    Raises
    ------
    Exception
        When any completion request fails.
    """
    ensure_openai_api_key()
    client = OpenAI()
    label_timestamp = get_current_timestamp()

    async def _run_all() -> tuple[list[dict], list[RequestUsage]]:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=LLM_CONCURRENCY) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    complete_one,
                    client,
                    task,
                    output_schema,
                    row_model,
                    system_prompt,
                    label_timestamp,
                )
                for task in tasks
            ]
            results = await asyncio.gather(*futures)
        rows = [pair[0] for pair in results]
        usage = [pair[1] for pair in results]
        return rows, usage

    started = clock()
    rows, usage = asyncio.run(_run_all())
    wall_seconds = clock() - started
    return ConcurrentRun(rows=rows, usage=usage, wall_seconds=wall_seconds)
