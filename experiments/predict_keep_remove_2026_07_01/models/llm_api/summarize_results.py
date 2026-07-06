"""Aggregate prompting results across llm_api leaf variants.

This script:
- scans all leaf `outputs/*/metadata.json` + `metrics.json`
- emits an aggregate CSV + Markdown table
- updates `HOW_TO_TRAIN_LANGUAGE_MODELS.md` and `results.md` with the latest table

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.models.llm_api.constants import (
    INPUT_MODE_TO_ABLATION_LABEL,
    MODEL_ID_BY_SIZE,
    PROMPT_TYPE_TO_LABEL,
)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _scan_variant_metadata(llm_api_root: Path) -> Iterable[tuple[Path, dict[str, Any], dict[str, Any]]]:
    """Yield (metadata_path, metadata, metrics) for each run."""
    for meta_path in llm_api_root.glob("*/*/*/outputs/*/metadata.json"):
        run_dir = meta_path.parent
        metrics_path = run_dir / "metrics.json"
        if not metrics_path.exists():
            continue

        meta = _read_json(meta_path)
        metrics = _read_json(metrics_path)
        yield meta_path, meta, metrics


def _md_table(df: pd.DataFrame) -> str:
    # Pandas defaults can reorder floats/formatting; keep stable.
    df2 = df.copy()
    numeric_cols = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
    ]
    for c in numeric_cols:
        if c in df2.columns:
            df2[c] = df2[c].map(lambda x: float(x) if x is not None else None)
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
        # Append a new marked section.
        content = content.rstrip() + "\n\n" + f"{begin}\n{new_table_md}\n{end}\n"

    file_path.write_text(content, encoding="utf-8")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    llm_api_root = Path(__file__).resolve().parent

    runs = list(_scan_variant_metadata(llm_api_root))
    if not runs:
        print("No completed llm_api runs found (no metrics.json).")
        return

    rows: list[dict[str, Any]] = []
    for _meta_path, meta, metrics in runs:
        prompt_type = meta["prompt_type"]
        input_mode = meta["input_mode"]
        model_name = meta["model_name"]
        # Keep leaf identity consistent with constants.
        model_size = meta.get("model_size")
        if model_size is None:
            # Best-effort inference.
            for sz, mid in MODEL_ID_BY_SIZE.items():
                if mid == model_name:
                    model_size = sz
                    break

        type_label = PROMPT_TYPE_TO_LABEL[prompt_type]
        ablation_label = INPUT_MODE_TO_ABLATION_LABEL[input_mode]

        train_m = metrics["train_metrics"]
        test_m = metrics["test_metrics"]

        for split_label, m in [("train", train_m), ("test", test_m)]:
            rows.append(
                {
                    "type": type_label,
                    "ablation": ablation_label,
                    "model_size": model_size,
                    "model_name": model_name,
                    "split": split_label,
                    "accuracy": m.get("accuracy"),
                    "precision": m.get("precision"),
                    "recall": m.get("recall"),
                    "f1": m.get("f1"),
                    "roc_auc": m.get("roc_auc"),
                    "pr_auc": m.get("pr_auc"),
                }
            )

    df = pd.DataFrame(rows)
    # Stable sort: type, ablation, model_size, model_name, split.
    sort_cols = ["type", "ablation", "model_size", "model_name", "split"]
    for c in sort_cols:
        if c not in df.columns:
            continue
    df = df.sort_values(sort_cols)

    table_md = _md_table(df)

    # Emit aggregate artifacts.
    timestamp = rows[0].get("timestamp") or ""
    out_dir = llm_api_root / "aggregate_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "aggregate_results.csv").write_text(
        df.to_csv(index=False),
        encoding="utf-8",
    )
    (out_dir / "aggregate_results.md").write_text(
        table_md,
        encoding="utf-8",
    )

    how_to = repo_root / "experiments/predict_keep_remove_2026_07_01/HOW_TO_TRAIN_LANGUAGE_MODELS.md"
    results_md = repo_root / "experiments/predict_keep_remove_2026_07_01/results.md"

    _update_marked_table(
        how_to,
        marker_name="LLM_PROMPTING_RESULTS_TABLE",
        new_table_md=table_md,
    )
    _update_marked_table(
        results_md,
        marker_name="LLM_PROMPTING_RESULTS_TABLE",
        new_table_md=table_md,
    )

    print("Aggregate prompting results table updated.")
    print(table_md)


if __name__ == "__main__":
    main()

