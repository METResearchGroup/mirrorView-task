"""Normalize prediction CSVs into a common frame.

The V0 long CSV currently includes only the primary Bedrock run
(`bedrock/qwen3-next-80b-a3b`). The llm_api adapter remains for optional
diagnostics if additional runs are added back to the manifest later.
"""

from __future__ import annotations

import pandas as pd

from collect.manifest import REPO_ROOT, RunSpec, canonical_runs


def _normalize_id_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "message_id" not in out.columns and "post_id" in out.columns:
        out["message_id"] = out["post_id"]
    if "message_id" not in out.columns:
        raise KeyError("Predictions missing message_id/post_id")
    out["message_id"] = out["message_id"].astype(str)
    out["post_id"] = out["message_id"]
    return out


def load_bedrock_predictions(run: RunSpec) -> pd.DataFrame:
    run_dir = REPO_ROOT / run.run_dir
    path = run_dir / "predictions.csv"
    df = pd.read_csv(path)
    df = _normalize_id_columns(df)
    required = {"message_id", "keep_remove_label", "predicted_label"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Bedrock preds missing columns {sorted(missing)}: {path}")
    return df[["post_id", "keep_remove_label", "predicted_label"]].copy()


def load_llm_api_predictions(run: RunSpec) -> pd.DataFrame:
    run_dir = REPO_ROOT / run.run_dir
    frames: list[pd.DataFrame] = []
    for name in run.prediction_files:
        path = run_dir / name
        part = pd.read_csv(path)
        part = _normalize_id_columns(part)
        required = {"message_id", "keep_remove_label", "predicted_label"}
        missing = required - set(part.columns)
        if missing:
            raise KeyError(f"llm_api preds missing columns {sorted(missing)}: {path}")
        frames.append(part[["post_id", "keep_remove_label", "predicted_label"]].copy())

    df = pd.concat(frames, ignore_index=True)
    # Train/test partitions are disjoint; still dedupe defensively.
    before = len(df)
    df = df.drop_duplicates(subset=["post_id"], keep="first")
    if len(df) != before:
        raise ValueError(
            f"llm_api train/test overlap for {run.classifier_id}: "
            f"{before} → {len(df)} after dedupe"
        )
    return df


def load_run_predictions(run: RunSpec) -> pd.DataFrame:
    if run.family == "bedrock":
        df = load_bedrock_predictions(run)
    elif run.family == "llm_api":
        df = load_llm_api_predictions(run)
    else:
        raise ValueError(f"Unsupported family {run.family!r} for {run.classifier_id}")

    if len(df) != run.expected_rows:
        raise ValueError(
            f"Unexpected row count for {run.classifier_id}: "
            f"got {len(df)}, expected {run.expected_rows}"
        )

    df = df.copy()
    df["classifier_id"] = run.classifier_id
    df["family"] = run.family
    df["ablation"] = run.ablation
    df["is_correct"] = (
        df["predicted_label"].astype(int) == df["keep_remove_label"].astype(int)
    ).astype(int)
    return df[
        [
            "post_id",
            "keep_remove_label",
            "predicted_label",
            "classifier_id",
            "family",
            "ablation",
            "is_correct",
        ]
    ]


def load_all_predictions(runs: list[RunSpec] | None = None) -> pd.DataFrame:
    runs = runs if runs is not None else canonical_runs()
    frames = [load_run_predictions(run) for run in runs]
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    preds = load_all_predictions()
    print(preds.groupby(["family", "classifier_id"]).size().to_string())
    print(f"total_rows={len(preds)}")
