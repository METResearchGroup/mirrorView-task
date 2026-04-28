"""CLI runner for mirrors content analyses.

Run this from the repository root and include `PYTHONPATH=.` so top-level
packages like `lib` resolve correctly.

Examples:
    PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026-04-24/run_analysis.py --help
    PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026-04-24/run_analysis.py --data-path scripts/mirrorview_pilot_data_2026-04-13.csv -a length_compression -f csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import questionary
import typer

from analysis.length_compression_analysis import run_analysis as run_length_compression
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

ANALYSIS_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "length_compression": run_length_compression,
}
AVAILABLE_FORMATS = ("csv", "jsonl")
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / "experiments" / "mirrors_content_analysis_2026-04-24" / "outputs"
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Run mirrors content analyses and write timestamped outputs.",
)


def _normalize_analyses(selected_analyses: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for analysis_name in selected_analyses:
        if analysis_name in seen:
            continue
        if analysis_name not in ANALYSIS_REGISTRY:
            raise ValueError(f"Unknown analysis '{analysis_name}'.")
        deduped.append(analysis_name)
        seen.add(analysis_name)
    return deduped


def _resolve_analyses(
    selected_analyses: list[str] | None,
) -> list[str]:
    if selected_analyses:
        return _normalize_analyses(selected_analyses)

    if not sys.stdin.isatty():
        raise typer.BadParameter(
            "No analyses provided. Use --analysis in non-interactive environments."
        )

    choices = sorted(ANALYSIS_REGISTRY.keys())
    prompt_result = questionary.checkbox(
        "Select analyses to run:",
        choices=choices,
        validate=lambda values: True if values else "Select at least one analysis.",
    ).ask()
    if not prompt_result:
        raise typer.Abort()
    return _normalize_analyses(prompt_result)


def _normalize_formats(formats: list[str]) -> list[str]:
    normalized = [fmt.strip().lower() for fmt in formats]
    invalid = [fmt for fmt in normalized if fmt not in AVAILABLE_FORMATS]
    if invalid:
        raise typer.BadParameter(
            f"Unsupported format(s): {invalid}. Allowed: {list(AVAILABLE_FORMATS)}."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for fmt in normalized:
        if fmt in seen:
            continue
        deduped.append(fmt)
        seen.add(fmt)
    return deduped


def _write_metadata(
    output_dir: Path,
    run_timestamp: str,
    dataset_path: str,
    selected_analyses: list[str],
    analysis_results: dict[str, dict[str, Any]],
    input_row_count: int,
) -> Path:
    metadata = {
        "run_timestamp": run_timestamp,
        "dataset_path": dataset_path,
        "selected_analyses": selected_analyses,
        "analysis_results": analysis_results,
        "input_row_count": input_row_count,
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


@app.command()
def run(
    data_path: Path = typer.Option(
        ...,
        "--data-path",
        help="Path to input dataset CSV.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    analyses: list[str] | None = typer.Option(
        None,
        "--analysis",
        "-a",
        help="Repeatable analysis selector. Omit to choose interactively.",
    ),
    output_root: Path = typer.Option(
        DEFAULT_OUTPUT_ROOT,
        "--output-root",
        help="Directory where timestamped output folders are created.",
        resolve_path=True,
    ),
    formats: list[str] = typer.Option(
        ["csv"],
        "--format",
        "-f",
        help="Repeatable output format flag: csv, jsonl.",
    ),
) -> None:
    selected_analyses = _resolve_analyses(analyses)
    selected_formats = _normalize_formats(formats)
    dataset_path_str = str(data_path)
    run_timestamp = get_current_timestamp()
    run_output_dir = output_root / run_timestamp
    run_output_dir.mkdir(parents=True, exist_ok=False)

    df = pd.read_csv(data_path)
    analysis_results: dict[str, dict[str, Any]] = {}

    for analysis_name in selected_analyses:
        analysis_fn = ANALYSIS_REGISTRY[analysis_name]
        result = analysis_fn(
            df=df,
            output_dir=run_output_dir,
            run_timestamp=run_timestamp,
            dataset_path=dataset_path_str,
            formats=selected_formats,
        )
        analysis_results[analysis_name] = result

    metadata_path = _write_metadata(
        output_dir=run_output_dir,
        run_timestamp=run_timestamp,
        dataset_path=dataset_path_str,
        selected_analyses=selected_analyses,
        analysis_results=analysis_results,
        input_row_count=int(len(df)),
    )

    print(f"Run timestamp: {run_timestamp}")
    print(f"Output directory: {run_output_dir}")
    print(f"Selected analyses: {', '.join(selected_analyses)}")
    print(f"Selected formats: {', '.join(selected_formats)}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    app()
