"""Aggregate Bedrock zero-shot baseline results across model variants.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.constants import (
    VARIANT_BY_SLUG,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    if "metrics" not in metrics:
        raise KeyError("metrics.json missing 'metrics'")
    return metrics["metrics"]


def _latest_run_dir(variant_folder: Path) -> Path | None:
    outputs_dir = variant_folder / "outputs"
    if not outputs_dir.is_dir():
        return None
    candidates = [
        p
        for p in outputs_dir.iterdir()
        if p.is_dir() and (p / "metrics.json").is_file() and (p / "metadata.json").is_file()
    ]
    if not candidates:
        return None
    complete = [p for p in candidates if _read_json(p / "metadata.json").get("status") == "complete"]
    return max(complete or candidates, key=lambda p: p.name)


def _scan_variant_metadata(api_baselines_root: Path) -> Iterable[tuple[Path, dict[str, Any], dict[str, Any]]]:
    for variant in VARIANT_BY_SLUG.values():
        run_dir = _latest_run_dir(api_baselines_root / variant.folder)
        if run_dir is None:
            continue
        meta_path = run_dir / "metadata.json"
        metrics_path = run_dir / "metrics.json"
        meta = _read_json(meta_path)
        metrics = _read_json(metrics_path)
        yield meta_path, meta, metrics


def _md_table(df: pd.DataFrame) -> str:
    df2 = df.copy()
    for col in ("accuracy", "precision", "recall", "f1"):
        if col in df2.columns:
            df2[col] = df2[col].map(lambda x: float(x) if x is not None else None)
    return df2.to_markdown(index=False)


def _update_marked_table(file_path: Path, *, marker_name: str, new_table_md: str) -> None:
    begin = f"<!-- BEGIN {marker_name} -->"
    end = f"<!-- END {marker_name} -->"
    content = file_path.read_text(encoding="utf-8")

    if begin in content and end in content and content.index(begin) < content.index(end):
        content = re.sub(
            rf"{re.escape(begin)}.*?{re.escape(end)}",
            f"{begin}\n{new_table_md}\n{end}",
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + f"{begin}\n{new_table_md}\n{end}\n"

    file_path.write_text(content, encoding="utf-8")


def main() -> None:
    experiment_root = Path(__file__).resolve().parents[3]
    api_baselines_root = Path(__file__).resolve().parent

    runs = list(_scan_variant_metadata(api_baselines_root))
    if not runs:
        print("No completed Bedrock baseline runs found (no metrics.json).")
        return

    rows: list[dict[str, Any]] = []
    for _meta_path, meta, metrics in runs:
        variant_slug = meta["variant_slug"]
        variant = VARIANT_BY_SLUG.get(variant_slug)
        model_label = variant.display_name if variant else variant_slug
        bedrock_model_id = meta.get("bedrock_model_id", "")
        split_metrics = _extract_metrics(metrics)

        rows.append(
            {
                "model": model_label,
                "bedrock_model_id": bedrock_model_id,
                "accuracy": split_metrics.get("accuracy"),
                "precision": split_metrics.get("precision"),
                "recall": split_metrics.get("recall"),
                "f1": split_metrics.get("f1"),
            }
        )

    df = pd.DataFrame(rows).sort_values(["model"])
    table_md = _md_table(df)

    out_dir = api_baselines_root / "aggregate_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "aggregate_results.csv").write_text(df.to_csv(index=False), encoding="utf-8")
    (out_dir / "aggregate_results.md").write_text(table_md, encoding="utf-8")

    how_to = experiment_root / "HOW_TO_TRAIN_LANGUAGE_MODELS.md"
    _update_marked_table(
        how_to,
        marker_name="LLM_FINETUNING_BASELINE_RESULTS_TABLE",
        new_table_md=table_md,
    )

    print("Aggregate Bedrock baseline results table updated.")
    print(table_md)


if __name__ == "__main__":
    main()
