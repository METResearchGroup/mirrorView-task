"""Temporary live smoke for OpenAI Batch partial success and interrupt-and-resume.

Delete this file before merge. Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode partial-success --feature is_news_or_opinion --post-count 3

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode interrupt --feature is_news_or_opinion --post-count 5 --stop-after-submit

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py \\
        --mode resume --feature is_news_or_opinion --run-dir /tmp/<printed-run-dir>
"""

from __future__ import annotations

import io
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer

from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchEngine,
    create_openai_client,
    submit_active_batch,
    wait_for_completed_batch,
)
from data_platform.generate_features.models import FeatureRunConfig, LabelTask
from data_platform.generate_features.openai_batch_state import (
    active_batch_state_path,
    load_active_batch_state,
)
from data_platform.generate_features.registry import FEATURE_REGISTRY

MODE_PARTIAL_SUCCESS = "partial-success"
MODE_INTERRUPT = "interrupt"
MODE_RESUME = "resume"
SMOKE_TASKS_FILENAME = "smoke_tasks.json"
SMOKE_BATCH_INDEX = 0
# Out of range for chat completions, so OpenAI rejects that one request with
# an HTTP 400 line in the error file while the rest of the batch completes.
# A bad model name would instead fail the whole batch at file validation.
BROKEN_TEMPERATURE = 5.0
SMOKE_TEXTS = (
    "The Senate passed the appropriations bill 61 to 38 on Tuesday evening.",
    "Honestly the new transit plan is a joke and everyone in charge should resign.",
    "just made the best grilled cheese of my life, no notes",
    "Officials confirmed the bridge will close for repairs starting next Monday.",
    "I think remote work made most of us better colleagues, not worse ones.",
    "anyone else's cat scream at 4am for no reason or is that just mine",
    "The central bank held interest rates steady, citing slowing inflation.",
    "Hot take: pineapple on pizza is fine and the discourse is exhausting.",
)


class _CountingFiles:
    """Wraps ``client.files`` to count uploads and optionally break one request line."""

    def __init__(self, inner: Any, counts: dict[str, int], break_custom_id: str | None) -> None:
        self._inner = inner
        self._counts = counts
        self._break_custom_id = break_custom_id

    def create(self, *, file: Any, purpose: str) -> Any:
        self._counts["files.create"] += 1
        if self._break_custom_id is None:
            return self._inner.create(file=file, purpose=purpose)
        lines = []
        for raw in file.read().decode("utf-8").splitlines():
            request = json.loads(raw)
            if request["custom_id"] == self._break_custom_id:
                request["body"]["temperature"] = BROKEN_TEMPERATURE
            lines.append(json.dumps(request))
        rewritten = io.BytesIO(("\n".join(lines) + "\n").encode("utf-8"))
        rewritten.name = "smoke_requests.jsonl"
        return self._inner.create(file=rewritten, purpose=purpose)

    def content(self, file_id: str) -> Any:
        return self._inner.content(file_id)


class _CountingBatches:
    """Wraps ``client.batches`` to count ``create`` calls."""

    def __init__(self, inner: Any, counts: dict[str, int]) -> None:
        self._inner = inner
        self._counts = counts

    def create(self, **kwargs: Any) -> Any:
        self._counts["batches.create"] += 1
        return self._inner.create(**kwargs)

    def retrieve(self, batch_id: str) -> Any:
        self._counts["batches.retrieve"] += 1
        return self._inner.retrieve(batch_id)


class CountingClient:
    """OpenAI client wrapper that counts provider calls for smoke evidence."""

    def __init__(self, break_custom_id: str | None = None) -> None:
        inner = create_openai_client()
        self.counts = {"files.create": 0, "batches.create": 0, "batches.retrieve": 0}
        self.files = _CountingFiles(inner.files, self.counts, break_custom_id)
        self.batches = _CountingBatches(inner.batches, self.counts)


def smoke_tasks(post_count: int) -> list[LabelTask]:
    """Return ``post_count`` fixed posts with stable smoke ids."""
    if post_count > len(SMOKE_TEXTS):
        raise ValueError(f"--post-count must be at most {len(SMOKE_TEXTS)}")
    return [
        LabelTask(uri=f"at://smoke/post/{index}", text=text)
        for index, text in enumerate(SMOKE_TEXTS[:post_count])
    ]


def _engine(feature: str, client: CountingClient) -> OpenAIBatchEngine:
    return OpenAIBatchEngine(
        FEATURE_REGISTRY[feature],
        FeatureRunConfig(),
        client,
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        _sleep,
    )


def _sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


def _label_chunk(
    feature: str, client: CountingClient, tasks: list[LabelTask], run_dir: Path
) -> tuple[list[dict], list[Any]]:
    rows: list[dict] = []
    failures = _engine(feature, client).label_chunk(
        tasks,
        feature_name=feature,
        run_dir=run_dir,
        batch_index=SMOKE_BATCH_INDEX,
        write_rows=rows.extend,
    )
    return rows, failures


def _print_state_after(run_dir: Path, feature: str) -> None:
    state = load_active_batch_state(run_dir, feature)
    print(f"active_state_after={'cleared' if state is None else state['state']}")


def run_partial_success(feature: str, post_count: int) -> None:
    """Break the last request so one line fails and the others succeed."""
    run_dir = Path(tempfile.mkdtemp(prefix="smoke_partial_"))
    tasks = smoke_tasks(post_count)
    client = CountingClient(break_custom_id=f"task-{post_count - 1:05d}")
    rows, failures = _label_chunk(feature, client, tasks, run_dir)
    print(f"run_dir={run_dir}")
    print(f"partial_success_rows={len(rows)}")
    print(f"partial_failure_rows={len(failures)}")
    for failure in failures:
        print(f"partial_failure={json.dumps(asdict(failure))}")
    print(f"provider_calls={json.dumps(client.counts)}")
    _print_state_after(run_dir, feature)


def run_interrupt(feature: str, post_count: int, stop_after_submit: bool, run_dir: Path | None) -> None:
    """Submit one job, persist state, and exit before any row is written."""
    run_dir = run_dir or Path(tempfile.mkdtemp(prefix="smoke_resume_"))
    tasks = smoke_tasks(post_count)
    (run_dir / SMOKE_TASKS_FILENAME).write_text(
        json.dumps([asdict(task) for task in tasks]), encoding="utf-8"
    )
    client = CountingClient()
    state = submit_active_batch(
        client,
        FEATURE_REGISTRY[feature],
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        tasks,
        run_dir=run_dir,
        feature_name=feature,
        batch_index=SMOKE_BATCH_INDEX,
        attempt_count=1,
    )
    print(f"run_dir={run_dir}")
    print(f"state_path={active_batch_state_path(run_dir, feature)}")
    print(f"batch_id={state['batch_id']}")
    print(f"input_file_id={state['input_file_id']}")
    print(f"state={state['state']}")
    print(f"provider_calls={json.dumps(client.counts)}")
    if not stop_after_submit:
        batch = wait_for_completed_batch(
            client, state["batch_id"], DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.poll_interval_seconds, _sleep
        )
        print(f"provider_status={batch.status}")
    print("resume with:")
    print(
        "PYTHONPATH=. uv run python data_platform/generate_features/smoke_resume_openai_batch.py "
        f"--mode resume --feature {feature} --run-dir {run_dir}"
    )


def run_resume(feature: str, run_dir: Path) -> None:
    """Reattach to the job saved by ``interrupt`` and label without a new submit."""
    state = load_active_batch_state(run_dir, feature)
    if state is None:
        raise FileNotFoundError(f"No active batch state under {run_dir}")
    tasks = [
        LabelTask(**task)
        for task in json.loads((run_dir / SMOKE_TASKS_FILENAME).read_text(encoding="utf-8"))
    ]
    print(f"state_before={json.dumps(state)}")
    client = CountingClient()
    rows, failures = _label_chunk(feature, client, tasks, run_dir)
    resubmitted = client.counts["files.create"] > 0 or client.counts["batches.create"] > 0
    print(f"reattached_batch_id={state['batch_id']}")
    print(f"completed_without_resubmit={'true' if not resubmitted else 'false'}")
    print(f"labeled_count={len(rows)}")
    print(f"failure_count={len(failures)}")
    print(f"provider_calls={json.dumps(client.counts)}")
    _print_state_after(run_dir, feature)


def main(
    mode: str = typer.Option(..., "--mode"),
    feature: str = typer.Option("is_news_or_opinion", "--feature"),
    post_count: int = typer.Option(3, "--post-count"),
    stop_after_submit: bool = typer.Option(False, "--stop-after-submit"),
    run_dir: Path | None = typer.Option(None, "--run-dir"),
) -> None:
    """Run one smoke mode: partial-success, interrupt, or resume."""
    if mode == MODE_PARTIAL_SUCCESS:
        run_partial_success(feature, post_count)
    elif mode == MODE_INTERRUPT:
        run_interrupt(feature, post_count, stop_after_submit, run_dir)
    elif mode == MODE_RESUME:
        if run_dir is None:
            raise typer.BadParameter("--run-dir is required for --mode resume")
        run_resume(feature, run_dir)
    else:
        raise typer.BadParameter(
            f"--mode must be one of {MODE_PARTIAL_SUCCESS}, {MODE_INTERRUPT}, {MODE_RESUME}"
        )


if __name__ == "__main__":
    typer.run(main)
