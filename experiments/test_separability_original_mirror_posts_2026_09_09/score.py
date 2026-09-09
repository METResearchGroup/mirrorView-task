"""Score separability labels against the gold presentation order.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    read_failed_ids,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    BINARY_NEGATIVE,
    BINARY_POSITIVE,
    CATALOG_SHA256,
    CATALOG_S3_URI,
    CELL_KEY_SEPARATOR,
    CELL_STANCE_ORDER,
    CELL_TOXICITY_ORDER,
    FAILED_SUMMARY_FORMAT,
    GOLD_HUMAN_SLOT_COLUMN,
    HUMAN_SLOT_COLUMN,
    ID_COLUMN,
    LABELS_ROOT_URI,
    METRIC_ROW_ORDER,
    OUTPUT_S3_BUCKET,
    OVERALL_ENGINE_ORDER,
    POSITIVE_HUMAN_SLOT,
    PRESENTATION_S3_KEY,
    PRINT_METRIC_ACCURACY,
    PRINT_METRIC_F1,
    PRINT_METRIC_PRECISION,
    PRINT_METRIC_RECALL,
    RESULTS_FILENAME,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    SAMPLED_STANCE_COLUMN,
    SOURCE_RECORD_ID_COLUMN,
    TOXICITY_LABEL_BY_SAMPLE_TYPE,
    ZERO_METRICS,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, DEFAULT_LLM_MODEL

PRESENTATION_S3_URI = f"s3://{OUTPUT_S3_BUCKET}/{PRESENTATION_S3_KEY}"
PRESENTATION_SHA256 = (
    "561611741b60157b7551ed2c5bf25395b488f17cdd61088979903405d5502fdc"
)
EXPERIMENT_COMMAND = (
    "experiments/test_separability_original_mirror_posts_2026_09_09/run.py"
)


def score_labels(
    presentations: pd.DataFrame,
    store: CampaignObjectStore,
    experiment_dir: Path,
) -> Path:
    """Join labels to presentations, print tables, and write RESULTS.md.

    Parameters
    ----------
    presentations
        Shared presentation table with gold slots.
    store
        Object store that holds engine final parquet files.
    experiment_dir
        Folder that receives ``RESULTS.md``.

    Returns
    -------
    Path
        Written results file path.
    """
    overall_rows = []
    cell_sections = []
    for engine in OVERALL_ENGINE_ORDER:
        joined, n_scored, n_failed = _load_engine_labels(engine, presentations, store)
        overall_rows.append(_overall_row(engine, joined, n_scored, n_failed))
        cell_sections.append(_cell_section(engine, joined, n_scored, n_failed))
    markdown = _results_markdown(overall_rows, cell_sections)
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(markdown)
    _print_tables(overall_rows, cell_sections)
    return path


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    """Compute accuracy, precision, recall, and F1 for the first-slot positive class."""
    return {
        PRINT_METRIC_ACCURACY: float(accuracy_score(y_true, y_pred)),
        PRINT_METRIC_PRECISION: float(
            precision_score(y_true, y_pred, zero_division=0)
        ),
        PRINT_METRIC_RECALL: float(recall_score(y_true, y_pred, zero_division=0)),
        PRINT_METRIC_F1: float(f1_score(y_true, y_pred, zero_division=0)),
    }


def _load_engine_labels(
    engine: str,
    presentations: pd.DataFrame,
    store: CampaignObjectStore,
) -> tuple[pd.DataFrame, int, int]:
    paths = FeaturePaths.from_root_uri(LABELS_ROOT_URI, engine)
    stored = store.get(paths.final_key)
    if stored is None:
        raise FileNotFoundError(paths.uri(paths.final_key))
    labels = pd.read_parquet(io.BytesIO(stored.body))
    joined = labels.merge(
        presentations,
        left_on=SOURCE_RECORD_ID_COLUMN,
        right_on=ID_COLUMN,
        how="inner",
    )
    valid = joined[joined[HUMAN_SLOT_COLUMN].isin(["first", "second"])]
    failed = len(read_failed_ids(store, paths))
    return valid, len(valid), failed


def _overall_row(
    engine: str, joined: pd.DataFrame, n_scored: int, n_failed: int
) -> dict[str, object]:
    metrics = _metrics_for_frame(joined)
    return {"engine": engine, "n_scored": n_scored, "n_failed": n_failed, **metrics}


def _cell_section(
    engine: str, joined: pd.DataFrame, n_scored: int, n_failed: int
) -> dict[str, object]:
    cells = {cell_key: _metrics_for_frame(group) for cell_key, group in _cell_groups(joined)}
    for column in _cell_columns():
        cells.setdefault(column, dict(ZERO_METRICS))
    return {
        "engine": engine,
        "cells": cells,
        "n_scored": n_scored,
        "n_failed": n_failed,
    }


def _cell_groups(joined: pd.DataFrame):
    grouped = joined.groupby([SAMPLED_STANCE_COLUMN, SAMPLE_TOXICITY_TYPE_COLUMN])
    for (stance, toxicity), group in grouped:
        yield _cell_key_from_values(str(stance), str(toxicity)), group


def _cell_key_from_values(stance: str, toxicity_type: str) -> str:
    toxicity = TOXICITY_LABEL_BY_SAMPLE_TYPE[toxicity_type]
    return f"{stance}{CELL_KEY_SEPARATOR}{toxicity}"


def _metrics_for_frame(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return dict(ZERO_METRICS)
    y_true = _binary_labels(frame[GOLD_HUMAN_SLOT_COLUMN])
    y_pred = _binary_labels(frame[HUMAN_SLOT_COLUMN])
    return compute_metrics(y_true, y_pred)


def _binary_labels(values: pd.Series) -> list[int]:
    return [
        BINARY_POSITIVE if str(value) == POSITIVE_HUMAN_SLOT else BINARY_NEGATIVE
        for value in values
    ]


def _results_markdown(
    overall_rows: list[dict[str, object]], cell_sections: list[dict[str, object]]
) -> str:
    lines = [
        "# Separability results",
        "",
        "## Commands",
        "",
        _command_block("--write-presentation"),
        "",
        "```bash",
        f"PYTHONPATH=. uv run python {EXPERIMENT_COMMAND} --engine openai --smoke",
        f"PYTHONPATH=. uv run python {EXPERIMENT_COMMAND} --engine bedrock --smoke",
        "```",
        "",
        "```bash",
        f"PYTHONPATH=. uv run python {EXPERIMENT_COMMAND} --engine openai",
        f"PYTHONPATH=. uv run python {EXPERIMENT_COMMAND} --engine bedrock",
        "```",
        "",
        _command_block("--score"),
        "",
        "## Catalog",
        "",
        f"Object `{CATALOG_S3_URI}` SHA-256 `{CATALOG_SHA256}`.",
        "",
        "## Presentation",
        "",
        f"Object `{PRESENTATION_S3_URI}` SHA-256 `{PRESENTATION_SHA256}`.",
        "",
        "## Models",
        "",
        f"OpenAI model `{DEFAULT_LLM_MODEL}`. Bedrock model `{DEFAULT_BEDROCK_NOVA_MICRO}`.",
        "",
        "## Overall",
        "",
        _overall_table(overall_rows),
    ]
    for section in cell_sections:
        lines.extend(["", f"## Cells {section['engine']}", "", _cell_table(section)])
    return "\n".join(lines) + "\n"


def _command_block(flag: str) -> str:
    return (
        "```bash\n"
        f"PYTHONPATH=. uv run python {EXPERIMENT_COMMAND} {flag}\n"
        "```"
    )


def _overall_table(rows: list[dict[str, object]]) -> str:
    header = (
        "| engine | accuracy | precision | recall | F1 |"
    )
    separator = "| ------ | --------: | ---------: | ------: | ---: |"
    body = [
        _overall_table_row(row)
        for row in rows
    ]
    footer = ["", *_overall_footer_lines(rows)]
    return "\n".join([header, separator, *body, *footer])


def _overall_footer_lines(rows: list[dict[str, object]]) -> list[str]:
    if not rows:
        return ["n_scored=0", "n_failed=0"]
    return [
        f"n_scored {row['engine']}={row['n_scored']}" for row in rows
    ] + [f"n_failed {row['engine']}={row['n_failed']}" for row in rows]


def _overall_table_row(row: dict[str, object]) -> str:
    return (
        f"| {row['engine']} | {row[PRINT_METRIC_ACCURACY]:.4f} | "
        f"{row[PRINT_METRIC_PRECISION]:.4f} | {row[PRINT_METRIC_RECALL]:.4f} | "
        f"{row[PRINT_METRIC_F1]:.4f} |"
    )


def _cell_table(section: dict[str, object]) -> str:
    columns = _cell_columns()
    header = "| metric | " + " | ".join(columns) + " |"
    separator = "| ------ | " + " | ".join("----:" for _ in columns) + " |"
    cells = section["cells"]
    body = [
        _cell_table_row(metric_name, cells, columns)
        for metric_name in METRIC_ROW_ORDER
    ]
    footer = [
        "",
        f"n_scored={section['n_scored']}",
        FAILED_SUMMARY_FORMAT.format(failed=section["n_failed"]),
    ]
    return "\n".join([header, separator, *body, *footer])


def _cell_columns() -> list[str]:
    return [
        f"{stance}{CELL_KEY_SEPARATOR}{toxicity}"
        for stance in CELL_STANCE_ORDER
        for toxicity in CELL_TOXICITY_ORDER
    ]


def _cell_table_row(
    metric_name: str, cells: dict[str, dict[str, float]], columns: list[str]
) -> str:
    values = [f"{cells.get(column, ZERO_METRICS)[metric_name]:.4f}" for column in columns]
    return "| " + metric_name + " | " + " | ".join(values) + " |"


def _print_tables(
    overall_rows: list[dict[str, object]], cell_sections: list[dict[str, object]]
) -> None:
    print(_overall_table(overall_rows))
    for section in cell_sections:
        print()
        print(_cell_table(section))
