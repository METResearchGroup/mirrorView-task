"""OpenAI Batch API helpers for post labeling.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batch_client
    print(batch_client.BATCH_ENDPOINT)
    "
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import BaseModel

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, llm_client, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import build_labeling_prompt
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import PostLabelResult

BYTES_PER_MIB = 1024 * 1024
BATCH_MAX_REQUESTS_PER_FILE = 50_000
BATCH_MAX_FILE_BYTES = 200 * BYTES_PER_MIB
BATCH_PRICE_FRACTION = 0.5
BATCH_ENDPOINT = "/v1/chat/completions"
BATCH_COMPLETION_WINDOW = "24h"
BATCH_FILE_PURPOSE = "batch"
BATCH_POLL_INTERVAL_SECONDS = 30.0
CHARS_PER_TOKEN_ESTIMATE = 4
OUTPUT_JSON_OVERHEAD_TOKENS = 24
OUTPUT_TOKENS_PER_FEATURE = 10
CUSTOM_ID_SEPARATOR = "__"
HTTP_OK = 200
STAGE_LABEL_BATCH = "label_batch"
STAGE_SELF_CONSISTENCY_BATCH = "self_consistency_batch"
TERMINAL_BATCH_STATUSES = frozenset({"completed", "failed", "expired", "cancelled"})


class OpenAIBatchClient(Protocol):
    """Subset of the OpenAI SDK client used for Batch labeling."""

    files: Any
    batches: Any


@dataclass(frozen=True)
class BatchCostEstimate:
    """Estimated token usage and USD for one Batch JSONL file."""

    n_requests: int
    input_tokens: int
    output_tokens: int
    projected_batch_usd: float
    cumulative_usd: float
    projected_total_usd: float


@dataclass(frozen=True)
class LabelShardRow:
    """One parsed label row for ``labels.jsonl``."""

    post_id: str
    text_surface: str
    labels: dict[str, bool]
    labeled_at: str


@dataclass(frozen=True)
class LabelTask:
    """One labeling request for Batch JSONL."""

    post_id: str
    text_surface: str
    text: str


def make_custom_id(post_id: str, text_surface: str) -> str:
    """Return the stable Batch ``custom_id`` for one post surface."""
    return f"{post_id}{CUSTOM_ID_SEPARATOR}{text_surface}"


def split_custom_id(custom_id: str) -> tuple[str, str]:
    """Split a ``custom_id`` into ``post_id`` and ``text_surface``."""
    post_id, text_surface = custom_id.split(CUSTOM_ID_SEPARATOR, maxsplit=1)
    return post_id, text_surface


def post_label_response_format(codebook: list[dict[str, Any]]) -> dict[str, Any]:
    """Return OpenAI ``response_format`` with one boolean property per feature."""
    feature_ids = [str(feature["feature_id"]) for feature in codebook]
    label_properties = {feature_id: {"type": "boolean"} for feature_id in feature_ids}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "PostLabelResult",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "object",
                        "properties": label_properties,
                        "required": feature_ids,
                        "additionalProperties": False,
                    }
                },
                "required": ["labels"],
                "additionalProperties": False,
            },
        },
    }


def build_batch_request_line(
    codebook: list[dict[str, Any]],
    post_id: str,
    text: str,
    text_surface: str,
) -> dict[str, Any]:
    """Build one OpenAI Batch JSONL request object."""
    messages = build_labeling_prompt(codebook, text, text_surface)
    return {
        "custom_id": make_custom_id(post_id, text_surface),
        "method": "POST",
        "url": BATCH_ENDPOINT,
        "body": {
            "model": constants.LLM_MODEL_ID,
            "reasoning_effort": constants.LLM_REASONING_EFFORT,
            "messages": messages,
            "response_format": post_label_response_format(codebook),
        },
    }


def build_batch_jsonl_from_tasks(
    tasks: list[LabelTask],
    codebook: list[dict[str, Any]],
    output_dir: Path,
) -> list[Path]:
    """Write Batch JSONL from explicit per-surface tasks."""
    lines = [
        build_batch_request_line(codebook, task.post_id, task.text, task.text_surface)
        for task in tasks
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    return _write_jsonl_chunks(lines, output_dir)


def build_batch_jsonl(
    posts: list[dict[str, str]],
    codebook: list[dict[str, Any]],
    text_surfaces: tuple[str, ...],
    output_dir: Path,
    skip_custom_ids: set[str] | None = None,
) -> list[Path]:
    """Write Batch request JSONL file(s) and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = _collect_request_lines(posts, codebook, text_surfaces, skip_custom_ids or set())
    return _write_jsonl_chunks(lines, output_dir)


def estimate_batch_cost(jsonl_paths: list[Path], feature_count: int) -> BatchCostEstimate:
    """Estimate Batch USD from JSONL size and feature count."""
    n_requests = 0
    input_chars = 0
    for path in jsonl_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            n_requests += 1
            input_chars += len(line)
    input_tokens = max(input_chars // CHARS_PER_TOKEN_ESTIMATE, 0)
    output_tokens = n_requests * (
        OUTPUT_JSON_OVERHEAD_TOKENS + feature_count * OUTPUT_TOKENS_PER_FEATURE
    )
    projected_batch_usd = compute_batch_cost_usd(input_tokens, output_tokens)
    cumulative_usd = llm_client.read_cumulative_cost_usd()
    projected_total_usd = cumulative_usd + projected_batch_usd
    return BatchCostEstimate(
        n_requests=n_requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        projected_batch_usd=projected_batch_usd,
        cumulative_usd=cumulative_usd,
        projected_total_usd=projected_total_usd,
    )


def compute_batch_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Return USD at Batch rates (50% of standard)."""
    standard = llm_client.compute_cost_usd(input_tokens, output_tokens, cached_input_tokens)
    return standard * BATCH_PRICE_FRACTION


def append_batch_cost_log(
    *,
    stage: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
    cached_input_tokens: int = 0,
) -> float:
    """Append one Batch-priced line to the shared cost log."""
    cost_usd = compute_batch_cost_usd(input_tokens, output_tokens, cached_input_tokens)
    return llm_client.append_cost_log(
        stage=stage,
        arm=None,
        model=constants.LLM_MODEL_ID,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        cost_usd=cost_usd,
    )


def submit_batch(client: OpenAIBatchClient, jsonl_path: Path) -> str:
    """Upload one JSONL file and create a Batch job."""
    file_id = _upload_jsonl(client, jsonl_path)
    batch = client.batches.create(
        input_file_id=file_id,
        endpoint=BATCH_ENDPOINT,
        completion_window=BATCH_COMPLETION_WINDOW,
    )
    return batch.id


def poll_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    sleep_fn: Callable[[float], None] | None = None,
    timeout_seconds: float | None = None,
) -> Any:
    """Poll until the Batch reaches a terminal status."""
    sleeper = sleep_fn or time.sleep
    started = time.monotonic()
    while True:
        batch = client.batches.retrieve(batch_id)
        if batch.status in TERMINAL_BATCH_STATUSES:
            return batch
        if timeout_seconds is not None and time.monotonic() - started >= timeout_seconds:
            return batch
        sleeper(BATCH_POLL_INTERVAL_SECONDS)


def download_results(client: OpenAIBatchClient, batch: Any) -> tuple[list[str], list[str]]:
    """Download output and error JSONL text lines for one Batch."""
    output_lines = _download_file_lines(client, getattr(batch, "output_file_id", None))
    error_lines = _download_file_lines(client, getattr(batch, "error_file_id", None))
    return output_lines, error_lines


def parse_batch_output(output_lines: list[str]) -> list[LabelShardRow]:
    """Parse successful Batch output lines into label shard rows."""
    rows: list[LabelShardRow] = []
    for line in output_lines:
        if not line.strip():
            continue
        row = _parse_output_line(line)
        if row is not None:
            rows.append(row)
    return rows


def resubmit_missing(
    posts: list[dict[str, str]],
    codebook: list[dict[str, Any]],
    text_surfaces: tuple[str, ...],
    present_custom_ids: set[str],
    output_dir: Path,
) -> list[Path]:
    """Build JSONL containing only ``custom_id`` values not yet present."""
    return build_batch_jsonl(
        posts,
        codebook,
        text_surfaces,
        output_dir,
        skip_custom_ids=present_custom_ids,
    )


def write_label_shard_rows(shard_path: Path, rows: list[LabelShardRow]) -> None:
    """Append label rows to ``labels.jsonl``."""
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    with shard_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "post_id": row.post_id,
                "text_surface": row.text_surface,
                "labels": row.labels,
                "labeled_at": row.labeled_at,
            }
            handle.write(json.dumps(payload) + "\n")


def collect_usage_from_output_lines(output_lines: list[str]) -> dict[str, int]:
    """Sum token usage from Batch output JSONL lines."""
    totals = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    for line in output_lines:
        if not line.strip():
            continue
        payload = json.loads(line)
        usage = (payload.get("response") or {}).get("body", {}).get("usage") or {}
        totals["input_tokens"] += int(usage.get("prompt_tokens", 0))
        totals["output_tokens"] += int(usage.get("completion_tokens", 0))
        totals["reasoning_tokens"] += int(usage.get("reasoning_tokens", 0))
    return totals


def get_openai_client() -> OpenAIBatchClient:
    """Return an OpenAI client using the environment API key."""
    from openai import OpenAI

    return OpenAI()


def _collect_request_lines(
    posts: list[dict[str, str]],
    codebook: list[dict[str, Any]],
    text_surfaces: tuple[str, ...],
    skip_custom_ids: set[str],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for post in posts:
        for surface in text_surfaces:
            custom_id = make_custom_id(post["post_id"], surface)
            if custom_id in skip_custom_ids:
                continue
            text = _surface_text(post, surface)
            lines.append(build_batch_request_line(codebook, post["post_id"], text, surface))
    return lines


def _surface_text(post: dict[str, str], text_surface: str) -> str:
    if text_surface == "mirror":
        return post["mirror_text"]
    return post["original_text"]


def _write_jsonl_chunks(lines: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    chunk: list[dict[str, Any]] = []
    chunk_index = 0
    for line in lines:
        chunk.append(line)
        if len(chunk) >= BATCH_MAX_REQUESTS_PER_FILE:
            paths.append(_flush_chunk(chunk, output_dir, chunk_index))
            chunk_index += 1
            chunk = []
    if chunk:
        paths.append(_flush_chunk(chunk, output_dir, chunk_index))
    return paths


def _flush_chunk(chunk: list[dict[str, Any]], output_dir: Path, chunk_index: int) -> Path:
    path = output_dir / f"batch_input_{chunk_index:03d}.jsonl"
    text = "\n".join(json.dumps(row) for row in chunk) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _upload_jsonl(client: OpenAIBatchClient, jsonl_path: Path) -> str:
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".jsonl") as handle:
        handle.write(jsonl_path.read_bytes())
        handle.flush()
        handle.seek(0)
        uploaded = client.files.create(file=handle.file, purpose=BATCH_FILE_PURPOSE)
    return uploaded.id


def _download_file_lines(client: OpenAIBatchClient, file_id: str | None) -> list[str]:
    if file_id is None:
        return []
    content = client.files.content(file_id)
    text = content.text if hasattr(content, "text") else content.read().decode("utf-8")
    return text.splitlines()


def _parse_output_line(line: str) -> LabelShardRow | None:
    payload = json.loads(line)
    response = payload.get("response") or {}
    if response.get("status_code") != HTTP_OK:
        return None
    body = response.get("body") or {}
    content = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not content:
        return None
    parsed = PostLabelResult.model_validate_json(content)
    post_id, text_surface = split_custom_id(payload["custom_id"])
    labeled_at = datetime.now(timezone.utc).isoformat()
    return LabelShardRow(
        post_id=post_id,
        text_surface=text_surface,
        labels=dict(parsed.labels),
        labeled_at=labeled_at,
    )

