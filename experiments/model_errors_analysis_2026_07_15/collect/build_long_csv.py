"""Join texts + labels → classifier_post_results_long.csv.

Does not call Bedrock. Reads only existing prediction CSVs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Allow `python collect/build_long_csv.py` from the experiment root.
_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from collect.load_predictions import load_all_predictions
from collect.manifest import (
    LONG_CSV_COLUMNS,
    MANIFEST_PATH,
    OUTPUTS_DIR,
    REPO_ROOT,
    build_manifest,
    canonical_runs,
)

PKR_ROOT = REPO_ROOT / "experiments" / "predict_keep_remove_2026_07_01"
LONG_CSV_PATH = OUTPUTS_DIR / "classifier_post_results_long.csv"
ACCURACY_TOL = 1e-6


def _load_training_dataframe() -> pd.DataFrame:
    # Dataloader package imports via experiments.predict_keep_remove_...
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from experiments.predict_keep_remove_2026_07_01.data.dataloader import (  # noqa: WPS433
        Dataloader,
    )

    return Dataloader().load_training_dataframe()


def _join_texts(preds: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    texts = labels.rename(
        columns={
            "message_id": "post_id",
            "mirror_text": "mirrored_text",
            "keep_remove_label": "label",
        }
    )[["post_id", "original_text", "mirrored_text", "label"]].copy()
    texts["post_id"] = texts["post_id"].astype(str)

    merged = preds.merge(texts, on="post_id", how="left", validate="many_to_one")
    missing = merged["original_text"].isna() | merged["mirrored_text"].isna() | merged["label"].isna()
    if missing.any():
        bad_ids = merged.loc[missing, "post_id"].unique()[:5]
        raise ValueError(
            f"Join failed for {int(missing.sum())} rows; example post_ids={list(bad_ids)}"
        )

    # Pred keep_remove_label must match study label.
    label_mismatch = merged["keep_remove_label"].astype(int) != merged["label"].astype(int)
    if label_mismatch.any():
        n = int(label_mismatch.sum())
        example = merged.loc[label_mismatch, ["post_id", "classifier_id"]].head(3)
        raise ValueError(f"keep_remove_label mismatch vs study labels on {n} rows:\n{example}")

    # Recompute is_correct from joined label (should match pred-side compute).
    recomputed = (
        merged["predicted_label"].astype(int) == merged["label"].astype(int)
    ).astype(int)
    if not (recomputed == merged["is_correct"].astype(int)).all():
        raise ValueError("is_correct inconsistent after join")

    out = merged[
        [
            "post_id",
            "original_text",
            "mirrored_text",
            "label",
            "classifier_id",
            "family",
            "ablation",
            "is_correct",
        ]
    ].copy()
    out["label"] = out["label"].astype(int)
    out["is_correct"] = out["is_correct"].astype(int)
    return out


def _assert_schema(df: pd.DataFrame) -> None:
    if list(df.columns) != list(LONG_CSV_COLUMNS):
        raise AssertionError(
            f"Column mismatch.\nexpected={list(LONG_CSV_COLUMNS)}\ngot={list(df.columns)}"
        )
    families = set(df["family"].unique())
    if not families.issubset({"bedrock", "llm_api"}):
        raise AssertionError(f"Unexpected families: {sorted(families)}")
    dup = df.duplicated(subset=["post_id", "classifier_id"], keep=False)
    if dup.any():
        raise AssertionError(f"Duplicate (post_id, classifier_id) rows: {int(dup.sum())}")


def _assert_label_distribution(df: pd.DataFrame, labels: pd.DataFrame) -> None:
    # Per-classifier label counts should match the training dataframe.
    study = labels["keep_remove_label"].astype(int).value_counts().sort_index()
    for clf, part in df.groupby("classifier_id"):
        got = part["label"].astype(int).value_counts().sort_index()
        if not got.equals(study):
            raise AssertionError(
                f"Label distribution mismatch for {clf}:\nstudy={study.to_dict()}\ngot={got.to_dict()}"
            )


def _accuracy_from_metrics(metrics: dict, family: str) -> float | None:
    """Return overall accuracy to compare against long-CSV accuracy when possible."""
    if family == "bedrock":
        m = metrics.get("metrics") or metrics
        if "accuracy" in m:
            return float(m["accuracy"])
        return None

    # llm_api: metrics split into train/test; overall = weighted by row counts if present.
    train = metrics.get("train_metrics") or {}
    test = metrics.get("test_metrics") or {}
    if "accuracy" in train and "accuracy" in test:
        # Prefer exact overall from confusion if available; else use split sizes from metadata later.
        return None  # handled with confusion matrices below
    return None


def _overall_accuracy_from_llm_api_metrics(metrics: dict) -> float | None:
    train = metrics.get("train_metrics") or {}
    test = metrics.get("test_metrics") or {}
    keys = (
        "confusion_matrix_tn",
        "confusion_matrix_fp",
        "confusion_matrix_fn",
        "confusion_matrix_tp",
    )
    if all(k in train for k in keys) and all(k in test for k in keys):
        correct = (
            float(train["confusion_matrix_tn"])
            + float(train["confusion_matrix_tp"])
            + float(test["confusion_matrix_tn"])
            + float(test["confusion_matrix_tp"])
        )
        total = correct + (
            float(train["confusion_matrix_fp"])
            + float(train["confusion_matrix_fn"])
            + float(test["confusion_matrix_fp"])
            + float(test["confusion_matrix_fn"])
        )
        if total <= 0:
            return None
        return correct / total
    return None


def _assert_accuracy_vs_metrics(df: pd.DataFrame, manifest: dict) -> None:
    by_clf = {r["classifier_id"]: r for r in manifest["runs"]}
    for clf, part in df.groupby("classifier_id"):
        entry = by_clf[clf]
        metrics_path = entry.get("metrics_path")
        if not metrics_path:
            continue
        metrics = json.loads((REPO_ROOT / metrics_path).read_text(encoding="utf-8"))
        long_acc = float(part["is_correct"].mean())

        if entry["family"] == "bedrock":
            expected = _accuracy_from_metrics(metrics, "bedrock")
        else:
            expected = _overall_accuracy_from_llm_api_metrics(metrics)

        if expected is None:
            continue
        if abs(long_acc - expected) > ACCURACY_TOL:
            raise AssertionError(
                f"Accuracy mismatch for {clf}: long_csv={long_acc:.10f} metrics={expected:.10f}"
            )


def build_long_csv(*, write: bool = True) -> pd.DataFrame:
    manifest = build_manifest(write=write)
    runs = canonical_runs()
    preds = load_all_predictions(runs)
    labels = _load_training_dataframe()
    long_df = _join_texts(preds, labels)

    _assert_schema(long_df)
    _assert_label_distribution(long_df, labels)
    _assert_accuracy_vs_metrics(long_df, manifest)

    expected_rows = manifest["expected_long_csv_rows"]
    if len(long_df) != expected_rows:
        raise AssertionError(f"Expected {expected_rows} long rows, got {len(long_df)}")

    if write:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        long_df.to_csv(LONG_CSV_PATH, index=False)

    return long_df


def main() -> None:
    df = build_long_csv(write=True)
    print(f"Wrote {LONG_CSV_PATH.relative_to(REPO_ROOT)}")
    print(f"Wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"rows={len(df)} classifiers={df['classifier_id'].nunique()}")
    print(df.groupby(["family", "classifier_id"])["is_correct"].agg(["count", "mean"]).to_string())


if __name__ == "__main__":
    main()
