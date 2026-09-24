"""LiteLLM structured completion client with spend logging.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client \\
      --probe
"""

from __future__ import annotations

import argparse
import importlib
import json
import multiprocessing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths

TOKENS_PER_MILLION = 1_000_000
METADATA_FILENAME = "metadata.json"
REQUEST_TIMEOUT_SECONDS = 180
MAX_COMPLETION_ATTEMPTS = 2
ALLOWED_OPENAI_PARAMS = ("reasoning_effort",)


class SpendCapExceeded(Exception):
    """Raised when a call would exceed the cumulative spend cap."""


class ProbeResult(BaseModel):
    """Minimal structured response for the probe CLI."""

    ok: bool = Field(description="True when the probe succeeds.")


def make_run_timestamp() -> str:
    """Return a per-call timestamp string for artifact filenames."""
    return datetime.now().strftime(constants.RUN_TIMESTAMP_FORMAT)


def read_cumulative_cost_usd() -> float:
    """Return cumulative spend from the shared cost log."""
    cost_log = paths.cost_log_path()
    if not cost_log.is_file():
        return 0.0
    last_line = ""
    for line in cost_log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last_line = line
    if not last_line:
        return 0.0
    record = json.loads(last_line)
    return float(record.get("cumulative_cost_usd", 0.0))


def append_cost_log(
    *,
    stage: str,
    arm: str | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    cost_usd: float,
) -> float:
    """Append one cost log line and return the new cumulative total."""
    cumulative = read_cumulative_cost_usd() + cost_usd
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "arm": arm,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cost_usd": cost_usd,
        "cumulative_cost_usd": cumulative,
    }
    cost_log = paths.cost_log_path()
    cost_log.parent.mkdir(parents=True, exist_ok=True)
    with cost_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return cumulative


def complete_structured(
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
    *,
    stage: str,
    arm: str | None,
    call_index: int,
    output_dir: Path,
    run_metadata: dict[str, Any],
) -> BaseModel:
    """Run one structured LiteLLM completion and write per-call artifacts."""
    _ensure_under_spend_cap()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_text, usage = _call_litellm(messages, response_model)
    parsed = response_model.model_validate_json(raw_text)
    artifact_path = _write_call_artifact(output_dir, call_index, messages, raw_text, parsed, usage)
    _record_call_cost(stage, arm, usage)
    return parsed


def _ensure_under_spend_cap() -> None:
    if read_cumulative_cost_usd() >= constants.SPEND_CAP_USD:
        raise SpendCapExceeded(f"cumulative spend reached {constants.SPEND_CAP_USD}")


def _call_litellm(
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
) -> tuple[str, dict[str, int]]:
    last_error: Exception | None = None
    for attempt in range(MAX_COMPLETION_ATTEMPTS):
        _ensure_under_spend_cap()
        try:
            return _litellm_completion(messages, response_model)
        except TimeoutError as exc:
            last_error = exc
            if attempt + 1 >= MAX_COMPLETION_ATTEMPTS:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("litellm completion failed without an error")


def _litellm_completion(
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
) -> tuple[str, dict[str, int]]:
    return _completion_via_spawn(
        messages,
        constants.LLM_LITELLM_MODEL_ID,
        constants.LLM_REASONING_EFFORT,
        float(REQUEST_TIMEOUT_SECONDS),
        response_model.__module__,
        response_model.__name__,
    )


def _completion_via_spawn(
    messages: list[dict[str, str]],
    model_id: str,
    reasoning_effort: str,
    timeout: float,
    model_module: str,
    model_class: str,
) -> tuple[str, dict[str, int]]:
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_child_litellm_worker,
        args=(child_conn, messages, model_id, reasoning_effort, timeout, model_module, model_class),
    )
    proc.start()
    child_conn.close()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        parent_conn.close()
        raise TimeoutError(f"litellm completion exceeded {int(timeout)}s")
    return _read_child_completion(parent_conn)


def _read_child_completion(parent_conn: Any) -> tuple[str, dict[str, int]]:
    if not parent_conn.poll():
        parent_conn.close()
        raise RuntimeError("litellm child exited without a result")
    status, payload, usage = parent_conn.recv()
    parent_conn.close()
    if status == "err":
        raise RuntimeError(str(payload))
    return str(payload), dict(usage or {})


def _child_litellm_worker(
    conn: Any,
    messages: list[dict[str, str]],
    model_id: str,
    reasoning_effort: str,
    timeout: float,
    model_module: str,
    model_class: str,
) -> None:
    try:
        raw, usage = _child_run_litellm(
            messages, model_id, reasoning_effort, timeout, model_module, model_class
        )
        conn.send(("ok", raw, usage))
    except Exception as exc:
        conn.send(("err", repr(exc), {}))
    finally:
        conn.close()


def _child_run_litellm(
    messages: list[dict[str, str]],
    model_id: str,
    reasoning_effort: str,
    timeout: float,
    model_module: str,
    model_class: str,
) -> tuple[str, dict[str, int]]:
    import litellm

    model_type = getattr(importlib.import_module(model_module), model_class)
    litellm.num_retries = 0
    litellm.request_timeout = int(timeout)
    response = litellm.completion(
        model=model_id,
        messages=messages,
        response_format=model_type,
        reasoning_effort=reasoning_effort,
        allowed_openai_params=list(ALLOWED_OPENAI_PARAMS),
        timeout=timeout,
        max_retries=0,
    )
    raw_text = response.choices[0].message.content or ""
    return raw_text, _extract_usage(response)


def _record_call_cost(stage: str, arm: str | None, usage: dict[str, int]) -> None:
    cost_usd = compute_cost_usd(
        usage["input_tokens"],
        usage["output_tokens"],
        usage.get("cached_input_tokens", 0),
    )
    append_cost_log(
        stage=stage,
        arm=arm,
        model=constants.LLM_MODEL_ID,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        reasoning_tokens=usage["reasoning_tokens"],
        cost_usd=cost_usd,
    )


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Return USD cost for one completion from token usage."""
    non_cached = max(input_tokens - cached_input_tokens, 0)
    return (
        non_cached * constants.LLM_INPUT_PRICE_PER_1M / TOKENS_PER_MILLION
        + cached_input_tokens * constants.LLM_CACHED_INPUT_PRICE_PER_1M / TOKENS_PER_MILLION
        + output_tokens * constants.LLM_OUTPUT_PRICE_PER_1M / TOKENS_PER_MILLION
    )


def merge_discovery_row(artifact_path: Path, discovery_row: dict[str, Any]) -> None:
    """Merge a discovery row into an existing per-call artifact."""
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    payload["discovery_row"] = discovery_row
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_probe() -> None:
    """Send a minimal structured completion and print probe diagnostics."""
    probe_dir = paths.EXPERIMENT_ROOT / "outputs" / "shared" / "probe"
    run_metadata = {
        "model": constants.LLM_MODEL_ID,
        "reasoning_effort": constants.LLM_REASONING_EFFORT,
        "stage": "probe",
        "litellm_model": constants.LLM_LITELLM_MODEL_ID,
        "timestamp_format": constants.RUN_TIMESTAMP_FORMAT,
    }
    parsed = complete_structured(
        [{"role": "user", "content": "Return ok=true."}],
        ProbeResult,
        stage="probe",
        arm=None,
        call_index=0,
        output_dir=probe_dir,
        run_metadata=run_metadata,
    )
    _write_run_metadata(probe_dir, run_metadata, sorted(probe_dir.glob("[0-9]*_*.json"))[-1])
    artifact = sorted(probe_dir.glob("[0-9]*_*.json"))[-1]
    usage = json.loads(artifact.read_text(encoding="utf-8"))["usage"]
    reasoning_tokens = usage.get("reasoning_tokens", 0)
    print(
        f"model={constants.LLM_LITELLM_MODEL_ID} "
        f"reasoning_effort={constants.LLM_REASONING_EFFORT} "
        f"reasoning_tokens={reasoning_tokens}"
    )
    if parsed.ok:
        print("probe_ok")


def _extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    input_tokens = _usage_int(usage, "prompt_tokens", "input_tokens")
    output_tokens = _usage_int(usage, "completion_tokens", "output_tokens")
    reasoning_tokens = _usage_int(usage, "reasoning_tokens")
    cached_input_tokens = _usage_int(usage, "cached_input_tokens", "cache_read_input_tokens")
    payload = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }
    if cached_input_tokens:
        payload["cached_input_tokens"] = cached_input_tokens
    return payload


def _usage_int(usage: Any, *names: str) -> int:
    for name in names:
        if isinstance(usage, dict):
            value = usage.get(name)
            if value is not None:
                return int(value)
            continue
        value = getattr(usage, name, None)
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _write_call_artifact(
    output_dir: Path,
    call_index: int,
    messages: list[dict[str, str]],
    raw_text: str,
    parsed: BaseModel,
    usage: dict[str, int],
) -> Path:
    call_timestamp = make_run_timestamp()
    artifact_path = output_dir / f"{call_index:05d}_{call_timestamp}.json"
    payload = {
        "request": {"messages": messages},
        "response": {"raw": raw_text, "parsed": parsed.model_dump()},
        "usage": usage,
    }
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def write_run_metadata(
    output_dir: Path,
    run_metadata: dict[str, Any],
    artifact_path: Path,
) -> None:
    """Write run-level metadata beside per-call artifacts."""
    _write_run_metadata(output_dir, run_metadata, artifact_path)


def _write_run_metadata(
    output_dir: Path,
    run_metadata: dict[str, Any],
    artifact_path: Path,
) -> None:
    metadata_path = output_dir / METADATA_FILENAME
    payload = {"run_metadata": run_metadata, "latest_artifact": artifact_path.name}
    metadata_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Parse CLI args and run the probe when requested."""
    parser = argparse.ArgumentParser(description="LiteLLM client utilities.")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        run_probe()
        return
    raise SystemExit("No command specified")


if __name__ == "__main__":
    main()
