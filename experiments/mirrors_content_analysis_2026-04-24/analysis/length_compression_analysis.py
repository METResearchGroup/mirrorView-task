"""Analysis 1: length and compression metrics for mirror text pairs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ANALYSIS_NAME = "length_compression"
PAIRWISE_FILENAME = "length_compression_pairwise.csv"
PAIRWISE_JSONL_FILENAME = "length_compression_pairwise.jsonl"
AGGREGATE_FILENAME = "length_compression_aggregate.csv"
KEEP_REMOVE_FILENAME = "length_compression_keep_remove.csv"

ID_COLUMNS = [
    "participant_id",
    "post_id",
    "decision",
    "evaluation_mode",
    "phase",
    "condition",
]

PUNCTUATION_RE = re.compile(r"[^\w\s]")
WORD_RE = re.compile(r"\b\w+\b")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value)


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def _sentence_count(text: str) -> int:
    parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    return len(parts)


def _punctuation_count(text: str) -> int:
    return len(PUNCTUATION_RE.findall(text))


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def _text_metrics(text: str) -> dict[str, float]:
    char_count = len(text)
    word_count = _word_count(text)
    sentence_count = _sentence_count(text)
    punctuation_count = _punctuation_count(text)
    avg_sentence_length = _safe_divide(word_count, sentence_count)
    punctuation_density = _safe_divide(punctuation_count, char_count)
    return {
        "char_count": float(char_count),
        "word_count": float(word_count),
        "sentence_count": float(sentence_count),
        "avg_sentence_length": avg_sentence_length,
        "punctuation_count": float(punctuation_count),
        "punctuation_density": punctuation_density,
    }


def _filter_mirror_pairs(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    mirror_non_empty = filtered["mirror_text"].fillna("").astype(str).str.strip().ne("")
    return filtered.loc[mirror_non_empty].copy()


def _build_pairwise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    present_id_cols = [col for col in ID_COLUMNS if col in df.columns]

    for _, row in df.iterrows():
        original_text = _normalize_text(row.get("original_text", ""))
        mirror_text = _normalize_text(row.get("mirror_text", ""))

        original_metrics = _text_metrics(original_text)
        mirror_metrics = _text_metrics(mirror_text)

        record: dict[str, Any] = {}
        for col in present_id_cols:
            record[col] = row[col]

        record["original_text"] = original_text
        record["mirror_text"] = mirror_text

        for metric_name, value in original_metrics.items():
            record[f"original_{metric_name}"] = value
        for metric_name, value in mirror_metrics.items():
            record[f"mirror_{metric_name}"] = value

        for metric_name in original_metrics:
            original_value = float(original_metrics[metric_name])
            mirror_value = float(mirror_metrics[metric_name])
            delta = mirror_value - original_value
            ratio = _safe_divide(mirror_value, original_value)
            record[f"delta_{metric_name}"] = delta
            record[f"ratio_{metric_name}"] = ratio

        rows.append(record)

    pairwise_df = pd.DataFrame(rows)
    return pairwise_df.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def _aggregate_for_group(
    pairwise_df: pd.DataFrame, group_name: str, group_value: str
) -> pd.DataFrame:
    metric_columns = [
        col
        for col in pairwise_df.columns
        if col.startswith(("original_", "mirror_", "delta_", "ratio_"))
        and col != "original_text"
        and col != "mirror_text"
    ]
    summary = pairwise_df[metric_columns].mean(numeric_only=True).to_frame().T
    summary.insert(0, "group_name", group_name)
    summary.insert(1, "group_value", str(group_value))
    summary.insert(2, "pair_count", int(len(pairwise_df)))
    return summary


def _build_aggregate_dataframe(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    frames = [_aggregate_for_group(pairwise_df, "overall", "all")]

    for group_col in ("decision", "evaluation_mode"):
        if group_col not in pairwise_df.columns:
            continue
        for group_value, group_df in pairwise_df.groupby(group_col, dropna=False):
            frames.append(_aggregate_for_group(group_df, group_col, str(group_value)))

    return pd.concat(frames, ignore_index=True)


def _build_keep_remove_dataframe(pairwise_df: pd.DataFrame) -> pd.DataFrame:
    if "decision" not in pairwise_df.columns:
        return _aggregate_for_group(pairwise_df, "decision", "missing")

    keep_remove = pairwise_df[
        pairwise_df["decision"].astype(str).str.lower().isin(["keep", "remove"])
    ].copy()
    if keep_remove.empty:
        return _aggregate_for_group(pairwise_df, "decision", "no_keep_remove_rows")

    frames = []
    for decision_value, group_df in keep_remove.groupby(
        keep_remove["decision"].astype(str).str.lower()
    ):
        frames.append(_aggregate_for_group(group_df, "decision", decision_value))
    return pd.concat(frames, ignore_index=True)


def _write_jsonl(df: pd.DataFrame, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as fp:
        for row in df.to_dict(orient="records"):
            fp.write(json.dumps(row, ensure_ascii=True) + "\n")


def run_analysis(
    df: pd.DataFrame,
    output_dir: Path,
    run_timestamp: str,
    dataset_path: str,
    formats: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Run length/compression analysis and write artifacts."""
    if "mirror_text" not in df.columns:
        raise ValueError("Input dataframe must contain 'mirror_text' column.")

    filtered_df = _filter_mirror_pairs(df)
    pairwise_df = _build_pairwise_dataframe(filtered_df)
    aggregate_df = _build_aggregate_dataframe(pairwise_df)
    keep_remove_df = _build_keep_remove_dataframe(pairwise_df)

    output_dir.mkdir(parents=True, exist_ok=True)
    pairwise_path = output_dir / PAIRWISE_FILENAME
    aggregate_path = output_dir / AGGREGATE_FILENAME
    keep_remove_path = output_dir / KEEP_REMOVE_FILENAME

    pairwise_df.to_csv(pairwise_path, index=False)
    aggregate_df.to_csv(aggregate_path, index=False)
    keep_remove_df.to_csv(keep_remove_path, index=False)

    normalized_formats = {fmt.strip().lower() for fmt in (formats or [])}
    output_files = [PAIRWISE_FILENAME, AGGREGATE_FILENAME, KEEP_REMOVE_FILENAME]
    if "jsonl" in normalized_formats:
        jsonl_path = output_dir / PAIRWISE_JSONL_FILENAME
        _write_jsonl(pairwise_df, jsonl_path)
        output_files.append(PAIRWISE_JSONL_FILENAME)

    return {
        "analysis_name": ANALYSIS_NAME,
        "output_files": output_files,
        "row_counts": {
            "input_rows": int(len(df)),
            "mirror_non_empty_rows": int(len(filtered_df)),
            "pairwise_rows": int(len(pairwise_df)),
            "aggregate_rows": int(len(aggregate_df)),
            "keep_remove_rows": int(len(keep_remove_df)),
        },
        "notes": [
            f"run_timestamp={run_timestamp}",
            f"dataset_path={dataset_path}",
            "analysis_scope=rows_with_non_empty_mirror_text",
        ],
    }
