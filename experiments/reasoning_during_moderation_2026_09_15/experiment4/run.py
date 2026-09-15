"""Score thinking traces and write RESULTS.md.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment1.run import (
    _read_jsonl,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment4.summarize import (
    marker_rates,
    paired_arm_comparison,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.artifacts import (
    download_if_missing,
    upload_under_prefix,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_OUTPUT_DIR,
    DEEPSEEK_MODEL_ID,
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    METADATA_FILENAME,
    METADATA_S3_KEY,
    QWEN_MODEL_ID,
)
from lib.constants import REPO_ROOT

MARKER_RATES_FILENAME = "marker_rates.csv"
ARM_COMPARISON_FILENAME = "arm_comparison.csv"
TOKEN_SUMMARY_FILENAME = "token_summary.csv"
RESPONSE_TIME_SUMMARY_FILENAME = "response_time_summary.csv"
RESULTS_FILENAME = "RESULTS.md"
EXPERIMENT4_OUTPUT_DIR = EXPERIMENT_DIR / "experiment4" / "outputs"
EXPERIMENT4_S3_PREFIX = f"{EXPERIMENT_S3_PREFIX}/experiment4/"
MISSING_TABLE_NOTE = "_No rows. GPU traces were not present in this environment._"
HUMAN_TIME_NOTE = "Values are milliseconds."
EMPTY_GPU_CLOSER = (
    "Human `response_time_ms` is in the experiment 3 table. Thinking-token counts "
    "and marker rates were not measured, because this environment had no GPU traces. "
    "F1 and accuracy are out of scope."
)
ZERO_DIFF = 0.0


def main() -> None:
    rates_path, comparison_path = _write_outputs()
    print("wrote_results=true")
    print(f"marker_rates={rates_path}")
    print(f"arm_comparison={comparison_path}")


def _write_outputs() -> tuple[Path, Path]:
    exp1 = _load_experiment_traces(EXPERIMENT_DIR / "experiment1" / "outputs")
    exp2 = _load_experiment_traces(EXPERIMENT_DIR / "experiment2" / "outputs")
    rates = marker_rates(pd.concat([exp1, exp2], ignore_index=True))
    comparison = paired_arm_comparison(exp1, exp2)
    rates_path = _write_csv(rates, MARKER_RATES_FILENAME)
    comparison_path = _write_csv(comparison, ARM_COMPARISON_FILENAME)
    _write_results(rates, comparison)
    _upload_output(rates_path)
    _upload_output(comparison_path)
    return rates_path, comparison_path


def _load_experiment_traces(output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model_id in (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID):
        name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
        path = output_dir / f"traces_{name}.jsonl"
        _download_optional(path)
        if path.is_file():
            rows.extend(_read_jsonl(path))
    return pd.DataFrame(rows)


def _download_optional(path: Path) -> None:
    if path.is_file():
        return
    try:
        download_if_missing(path, str(path.relative_to(REPO_ROOT)))
    except FileNotFoundError:
        return


def _write_csv(frame: pd.DataFrame, filename: str) -> Path:
    path = EXPERIMENT4_OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _write_results(rates: pd.DataFrame, comparison: pd.DataFrame) -> None:
    metadata = _load_metadata()
    exp1 = _read_csv_or_empty(
        EXPERIMENT_DIR / "experiment1" / "outputs" / TOKEN_SUMMARY_FILENAME
    )
    exp2 = _read_csv_or_empty(
        EXPERIMENT_DIR / "experiment2" / "outputs" / TOKEN_SUMMARY_FILENAME
    )
    exp3 = _read_csv_or_empty(
        EXPERIMENT_DIR / "experiment3" / "outputs" / RESPONSE_TIME_SUMMARY_FILENAME
    )
    text = _results_markdown(metadata, exp1, exp2, exp3, rates, comparison)
    (EXPERIMENT_DIR / RESULTS_FILENAME).write_text(text)


def _load_metadata() -> dict[str, object]:
    path = COHORT_OUTPUT_DIR / METADATA_FILENAME
    _download_optional_key(path, METADATA_S3_KEY)
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def _download_optional_key(path: Path, key: str) -> None:
    if path.is_file():
        return
    try:
        download_if_missing(path, key)
    except FileNotFoundError:
        return


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    _download_optional(path)
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def _results_markdown(
    metadata: dict[str, object],
    exp1: pd.DataFrame,
    exp2: pd.DataFrame,
    exp3: pd.DataFrame,
    rates: pd.DataFrame,
    comparison: pd.DataFrame,
) -> str:
    parts = [
        "# Reasoning tokens on split versus unanimous moderation posts",
        "",
        _metadata_block(metadata),
        "",
        *_section("Experiment 1", exp1),
        *_section("Experiment 2", exp2),
        *_section("Experiment 3", exp3, HUMAN_TIME_NOTE),
        "## Experiment 4",
        "",
        *_experiment4_body(rates, comparison),
        "",
        _paired_paragraph(comparison),
        "",
    ]
    return "\n".join(parts)


def _section(title: str, frame: pd.DataFrame, note: str = "") -> list[str]:
    extra = [note, ""] if note else []
    return [f"## {title}", "", *extra, _markdown_table(frame), ""]


def _experiment4_body(rates: pd.DataFrame, comparison: pd.DataFrame) -> list[str]:
    if rates.empty and comparison.empty:
        return [MISSING_TABLE_NOTE]
    return [_markdown_table(rates), "", _markdown_table(comparison)]


def _metadata_block(metadata: dict[str, object]) -> str:
    since_date = metadata.get("since_date", "unknown")
    csv_files = metadata.get("csv_files", "unknown")
    split = metadata.get("split", "unknown")
    keep = metadata.get("unanimous_keep", "unknown")
    remove = metadata.get("unanimous_remove", "unknown")
    return (
        f"Export `since_date={since_date}`, `csv_files={csv_files}`, "
        f"`split={split}`, `unanimous_keep={keep}`, `unanimous_remove={remove}`."
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return MISSING_TABLE_NOTE
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _unused in columns) + " |"
    rows = [_markdown_row(frame, index, columns) for index in range(len(frame))]
    return "\n".join([header, separator, *rows])


def _markdown_row(frame: pd.DataFrame, index: int, columns: list[str]) -> str:
    cells = [_format_cell(frame.iloc[index][column]) for column in columns]
    return "| " + " | ".join(cells) + " |"


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _paired_paragraph(comparison: pd.DataFrame) -> str:
    if comparison.empty:
        return EMPTY_GPU_CLOSER
    statements = [_diff_sentence(row) for _, row in comparison.iterrows()]
    return " ".join(statements) + " F1 and accuracy were not measured."


def _diff_sentence(row: pd.Series) -> str:
    diff = float(row["mean_thinking_token_diff"])
    direction = "lower" if diff < ZERO_DIFF else "not lower"
    return (
        f"{row['model_id']} {row['group']}: experiment 2 thinking-token mean is "
        f"{direction} than experiment 1 (diff={diff:.3f})."
    )


def _upload_output(path: Path) -> None:
    """Upload under the experiment 4 prefix. put_new when absent, else replace."""
    upload_under_prefix(path, EXPERIMENT4_S3_PREFIX)


if __name__ == "__main__":
    main()
