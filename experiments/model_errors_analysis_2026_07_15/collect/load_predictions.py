"""Normalize prediction CSVs into a common frame.

V0 labels CSV includes only the primary Bedrock run
(`bedrock/qwen3-next-80b-a3b`).
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


def load_run_predictions(run: RunSpec) -> pd.DataFrame:
    if run.family != "bedrock":
        raise ValueError(f"Unsupported family {run.family!r} for {run.classifier_id}")

    df = load_bedrock_predictions(run)

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
