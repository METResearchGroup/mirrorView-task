"""OpenAI Batch helpers shared across GPT-5.6 Terra experiment steps."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from data_platform.generate_features.engines.openai_engine import (
    CUSTOM_ID_PREFIX,
    OpenAIBatchClient,
    OpenAIBatchEngine,
    OpenAIBatchEngineConfig,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from pydantic import BaseModel

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    OPENAI_BATCH_COMPLETION_WINDOW,
    OPENAI_POLL_INTERVAL_SECONDS,
)


@dataclass(frozen=True)
class RequestUsage:
    """Token usage for one labeled record in a provider batch."""

    source_record_id: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class BatchRun:
    """Rows, per-request usage, and wall time for one provider batch."""

    rows: list[dict]
    usage: list[RequestUsage]
    wall_seconds: float


def build_feature_spec(
    name: str,
    row_model: type[BaseModel],
    system_prompt: str,
    output_schema: type[BaseModel],
) -> FeatureSpec:
    """Build an OpenAI Batch ``FeatureSpec`` for structured labeling.

    Parameters
    ----------
    name
        Feature registry name.
    row_model
        Pydantic model for validated label rows on disk.
    system_prompt
        System message sent to the model.
    output_schema
        Structured output schema for the completion.

    Returns
    -------
    FeatureSpec
        Spec with ``engine_type=\"openai\"``.
    """
    return FeatureSpec(
        name=name,
        model=row_model,
        engine_type="openai",
        system_prompt=system_prompt,
        llm_output_schema=output_schema,
    )


def build_engine(spec: FeatureSpec, client: OpenAIBatchClient) -> OpenAIBatchEngine:
    """Construct an OpenAI Batch engine with experiment model settings.

    Parameters
    ----------
    spec
        Feature specification for labeling.
    client
        OpenAI SDK client.

    Returns
    -------
    OpenAIBatchEngine
        Engine configured for this experiment's model and poll interval.
    """
    engine_config = OpenAIBatchEngineConfig(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        poll_interval_seconds=OPENAI_POLL_INTERVAL_SECONDS,
        completion_window=OPENAI_BATCH_COMPLETION_WINDOW,
        endpoint="/v1/chat/completions",
    )
    return OpenAIBatchEngine(
        spec,
        FeatureRunConfig(),
        client,
        engine_config,
        time.sleep,
    )


def parse_request_usage(output_text: str, ordered_ids: list[str]) -> list[RequestUsage]:
    """Parse per-request token usage from a batch output JSONL file.

    Parameters
    ----------
    output_text
        Raw JSONL text from ``output_file_id``.
    ordered_ids
        ``LabelTask.uri`` values in submission order.

    Returns
    -------
    list[RequestUsage]
        Usage aligned with ``ordered_ids``.

    Raises
    ------
    ValueError
        When a line is missing usage or custom ids do not match the task order.
    """
    usages: list[RequestUsage | None] = [None] * len(ordered_ids)
    for line in output_text.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        custom_id = payload.get("custom_id", "")
        if not custom_id.startswith(CUSTOM_ID_PREFIX):
            raise ValueError(f"unexpected custom_id {custom_id}")
        index = int(custom_id[len(CUSTOM_ID_PREFIX) :])
        if index < 0 or index >= len(ordered_ids):
            raise ValueError(f"custom_id index {index} out of range")
        response = payload.get("response") or {}
        body = response.get("body") or {}
        usage = body.get("usage")
        if not usage:
            raise ValueError(f"missing usage for {custom_id}")
        usages[index] = RequestUsage(
            source_record_id=ordered_ids[index],
            input_tokens=int(usage["prompt_tokens"]),
            output_tokens=int(usage["completion_tokens"]),
        )
    if any(entry is None for entry in usages):
        missing = [ordered_ids[i] for i, entry in enumerate(usages) if entry is None]
        raise ValueError(f"missing usage for tasks: {missing}")
    return [entry for entry in usages if entry is not None]


def run_batch(
    engine: OpenAIBatchEngine,
    client: OpenAIBatchClient,
    tasks: list[LabelTask],
    clock: Callable[[], float],
) -> BatchRun:
    """Run one provider batch and collect rows with token usage.

    Parameters
    ----------
    engine
        OpenAI Batch engine.
    client
        OpenAI SDK client for downloading the output file.
    tasks
        Label tasks submitted as one batch.
    clock
        Monotonic or wall clock callable.

    Returns
    -------
    BatchRun
        Parsed rows, usage, and elapsed seconds.
    """
    ordered_ids = [task.uri for task in tasks]
    started = clock()
    rows = engine.batch_label_records(tasks)
    wall_seconds = clock() - started
    batch = engine.last_batch
    if batch is None or batch.output_file_id is None:
        raise RuntimeError("batch finished without output_file_id")
    output_text = client.files.content(batch.output_file_id).text
    usage = parse_request_usage(output_text, ordered_ids)
    return BatchRun(rows=rows, usage=usage, wall_seconds=wall_seconds)
