"""Balanced logistic regression: Titan only_original → is_error.

Loads the shared ``split_ids.json`` (does **not** re-split). Fits
``LogisticRegression(class_weight='balanced')`` on train post IDs and evaluates
on test. Writes metrics, model, coefficients, and predictions under
``outputs/analysis/``.

Run from repo root::

    PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/linear_separator.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    ANALYSIS_META_PATH,
    ANALYSIS_TABLE_PATH,
    EMBEDDING_DIM,
    EMBEDDING_MATRIX_PATH,
    FEATURE_SET,
    LINEAR_SEPARATOR_COEFS_PATH,
    LINEAR_SEPARATOR_METRICS_PATH,
    LINEAR_SEPARATOR_MODEL_PATH,
    LINEAR_SEPARATOR_PREDS_PATH,
    LOGISTIC_METRICS_PATH,
    PRIMARY_CLASSIFIER_ID,
    PROGRESS_UPDATES_TRAIN_PATH,
    SPLIT_IDS_PATH,
    SPLIT_SEED,
    ANALYSIS_DIR,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def append_train_progress(lines: list[str]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PROGRESS_UPDATES_TRAIN_PATH.is_file():
        existing = PROGRESS_UPDATES_TRAIN_PATH.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    PROGRESS_UPDATES_TRAIN_PATH.write_text(existing + block, encoding="utf-8")


def load_split_ids() -> dict[str, Any]:
    if not SPLIT_IDS_PATH.is_file():
        raise FileNotFoundError(
            f"Missing shared split {SPLIT_IDS_PATH}. Run split.py first; "
            "do not re-split in this script."
        )
    payload = json.loads(SPLIT_IDS_PATH.read_text(encoding="utf-8"))
    required = {"train_post_ids", "test_post_ids", "seed", "feature_set", "classifier_id"}
    missing = required - set(payload)
    if missing:
        raise KeyError(f"split_ids.json missing keys: {sorted(missing)}")
    train_ids = [str(x) for x in payload["train_post_ids"]]
    test_ids = [str(x) for x in payload["test_post_ids"]]
    if set(train_ids) & set(test_ids):
        raise AssertionError("train/test overlap in split_ids.json")
    if payload.get("feature_set") != FEATURE_SET:
        raise ValueError(
            f"split feature_set={payload.get('feature_set')!r} != {FEATURE_SET!r}"
        )
    if payload.get("classifier_id") != PRIMARY_CLASSIFIER_ID:
        raise ValueError(
            f"split classifier_id={payload.get('classifier_id')!r} != "
            f"{PRIMARY_CLASSIFIER_ID!r}"
        )
    return payload


def load_xy() -> tuple[pd.DataFrame, np.ndarray]:
    """Load meta + embedding matrix; rows must align by post_id order."""
    if not EMBEDDING_MATRIX_PATH.is_file():
        raise FileNotFoundError(f"Missing {EMBEDDING_MATRIX_PATH}")
    if ANALYSIS_META_PATH.is_file():
        meta = pd.read_csv(ANALYSIS_META_PATH)
    elif ANALYSIS_TABLE_PATH.is_file():
        meta = pd.read_parquet(ANALYSIS_TABLE_PATH)
        keep = [c for c in ("post_id", "label", "is_correct", "is_error") if c in meta.columns]
        meta = meta[keep]
    else:
        raise FileNotFoundError(
            f"Missing meta ({ANALYSIS_META_PATH} or {ANALYSIS_TABLE_PATH})"
        )

    meta = meta.copy()
    meta["post_id"] = meta["post_id"].astype(str)
    for col in ("is_error", "is_correct", "label"):
        if col not in meta.columns:
            raise KeyError(f"meta missing column {col}")
        meta[col] = meta[col].astype(int)

    if meta["post_id"].duplicated().any():
        raise ValueError("Duplicate post_id in analysis meta")

    X = np.load(EMBEDDING_MATRIX_PATH)
    if X.ndim != 2 or X.shape[0] != len(meta) or X.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"X shape {X.shape} incompatible with meta n={len(meta)} dim={EMBEDDING_DIM}"
        )
    return meta, X.astype(np.float64, copy=False)


def index_by_ids(meta: pd.DataFrame, post_ids: list[str]) -> np.ndarray:
    """Return row indices into meta/X for the given post_ids (preserve split order)."""
    id_to_idx = {pid: i for i, pid in enumerate(meta["post_id"].tolist())}
    missing = [pid for pid in post_ids if pid not in id_to_idx]
    if missing:
        raise KeyError(f"{len(missing)} post_ids from split missing in meta (e.g. {missing[:3]})")
    return np.asarray([id_to_idx[pid] for pid in post_ids], dtype=np.int64)


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    solver="lbfgs",
                    random_state=SPLIT_SEED,
                ),
            ),
        ]
    )


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def _safe_ap(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(average_precision_score(y_true, y_score))


def evaluate_split(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y_true)),
        "n_error": int(y_true.sum()),
        "n_correct_class": int((1 - y_true).sum()),
        "error_rate": float(y_true.mean()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "roc_auc": _safe_auc(y_true, y_prob),
        "pr_auc": _safe_ap(y_true, y_prob),
        "precision_error": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_error": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_error": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "confusion_matrix": {
            "labels": [0, 1],
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
            "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=[0, 1],
            target_names=["correct (0)", "error (1)"],
            output_dict=True,
            zero_division=0,
        ),
    }


def write_metrics_partial(payload: dict[str, Any]) -> None:
    """Write metrics early / as we go (both canonical + alias paths)."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    LINEAR_SEPARATOR_METRICS_PATH.write_text(text, encoding="utf-8")
    LOGISTIC_METRICS_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    append_train_progress(
        [
            f"## {_utc_now()} — data load",
            "",
            f"- Loading shared split from `{SPLIT_IDS_PATH}` (no re-split)",
            f"- Features: `{EMBEDDING_MATRIX_PATH}` + `{ANALYSIS_META_PATH}`",
            "",
        ]
    )

    split = load_split_ids()
    meta, X = load_xy()
    train_ids = [str(x) for x in split["train_post_ids"]]
    test_ids = [str(x) for x in split["test_post_ids"]]

    # Coverage: every meta post appears in exactly one split list
    all_split = set(train_ids) | set(test_ids)
    all_meta = set(meta["post_id"])
    if all_split != all_meta:
        raise AssertionError(
            f"split/meta coverage mismatch: "
            f"missing_in_split={len(all_meta - all_split)} "
            f"extra_in_split={len(all_split - all_meta)}"
        )

    train_idx = index_by_ids(meta, train_ids)
    test_idx = index_by_ids(meta, test_ids)
    X_train, y_train = X[train_idx], meta["is_error"].to_numpy()[train_idx]
    X_test, y_test = X[test_idx], meta["is_error"].to_numpy()[test_idx]

    print(
        f"Loaded X={X.shape} train={len(train_idx)} test={len(test_idx)} "
        f"err_train={y_train.mean():.4f} err_test={y_test.mean():.4f}"
    )
    append_train_progress(
        [
            f"## {_utc_now()} — data loaded",
            "",
            f"- n_train={len(train_idx)} n_test={len(test_idx)} seed={split.get('seed')}",
            f"- is_error rates: train={float(y_train.mean()):.4f} test={float(y_test.mean()):.4f}",
            f"- X shape={list(X.shape)} feature_set=`{FEATURE_SET}`",
            "",
        ]
    )

    # Partial metrics stub so artifacts exist before fit finishes
    write_metrics_partial(
        {
            "status": "loading_done",
            "updated_at": _utc_now(),
            "classifier_id": PRIMARY_CLASSIFIER_ID,
            "feature_set": FEATURE_SET,
            "target": "is_error",
            "positive_class": "error (is_error=1)",
            "split": {
                "path": str(SPLIT_IDS_PATH),
                "seed": split.get("seed"),
                "train_split": split.get("train_split"),
                "stratify_on": split.get("stratify_on"),
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "re_split": False,
            },
            "model": {
                "type": "Pipeline(StandardScaler, LogisticRegression)",
                "class_weight": "balanced",
                "solver": "lbfgs",
                "max_iter": 2000,
                "random_state": SPLIT_SEED,
            },
        }
    )

    pipe = build_pipeline()
    print("Fitting balanced logistic regression...")
    pipe.fit(X_train, y_train)
    append_train_progress(
        [
            f"## {_utc_now()} — train done",
            "",
            "- Fit `StandardScaler` + `LogisticRegression(class_weight='balanced')` on train only",
            f"- Model artifact pending write to `{LINEAR_SEPARATOR_MODEL_PATH}`",
            "",
        ]
    )

    train_prob = pipe.predict_proba(X_train)[:, 1]
    test_prob = pipe.predict_proba(X_test)[:, 1]
    train_pred = (train_prob >= 0.5).astype(int)
    test_pred = (test_prob >= 0.5).astype(int)

    train_metrics = evaluate_split(y_train, train_pred, train_prob)
    test_metrics = evaluate_split(y_test, test_pred, test_prob)

    clf: LogisticRegression = pipe.named_steps["clf"]
    coefs = clf.coef_.ravel()
    intercept = float(clf.intercept_.ravel()[0])
    feature_names = [f"orig_{i}" for i in range(EMBEDDING_DIM)]
    abs_order = np.argsort(-np.abs(coefs))
    top_k = 20
    top_coefs = [
        {
            "rank": int(r + 1),
            "feature": feature_names[int(i)],
            "dim": int(i),
            "coef": float(coefs[int(i)]),
            "abs_coef": float(abs(coefs[int(i)])),
        }
        for r, i in enumerate(abs_order[:top_k])
    ]

    metrics: dict[str, Any] = {
        "status": "complete",
        "updated_at": _utc_now(),
        "classifier_id": PRIMARY_CLASSIFIER_ID,
        "feature_set": FEATURE_SET,
        "target": "is_error",
        "positive_class": "error (is_error=1)",
        "threshold": 0.5,
        "split": {
            "path": str(SPLIT_IDS_PATH),
            "seed": split.get("seed"),
            "train_split": split.get("train_split"),
            "stratify_on": split.get("stratify_on"),
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "re_split": False,
        },
        "model": {
            "type": "Pipeline(StandardScaler, LogisticRegression)",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "max_iter": 2000,
            "random_state": SPLIT_SEED,
            "n_iter": int(np.max(clf.n_iter_)),
            "intercept": intercept,
        },
        "train": train_metrics,
        "test": test_metrics,
        "top_abs_coefficients": top_coefs,
        "artifacts": {
            "metrics": str(LINEAR_SEPARATOR_METRICS_PATH),
            "metrics_alias": str(LOGISTIC_METRICS_PATH),
            "model": str(LINEAR_SEPARATOR_MODEL_PATH),
            "coefficients": str(LINEAR_SEPARATOR_COEFS_PATH),
            "predictions": str(LINEAR_SEPARATOR_PREDS_PATH),
        },
        "interpretation": {
            "test_roc_auc": test_metrics["roc_auc"],
            "note": (
                "High test ROC-AUC (≫ 0.5) means Qwen errors are linearly organized "
                "in original-post Titan space; near 0.5 means not a single half-space."
            ),
        },
    }
    write_metrics_partial(metrics)

    # Persist model
    joblib.dump(
        {
            "pipeline": pipe,
            "feature_set": FEATURE_SET,
            "feature_names": feature_names,
            "target": "is_error",
            "classifier_id": PRIMARY_CLASSIFIER_ID,
            "split_path": str(SPLIT_IDS_PATH),
            "seed": split.get("seed"),
            "threshold": 0.5,
        },
        LINEAR_SEPARATOR_MODEL_PATH,
    )

    coef_df = pd.DataFrame(
        {
            "feature": feature_names,
            "dim": np.arange(EMBEDDING_DIM, dtype=int),
            "coef": coefs,
            "abs_coef": np.abs(coefs),
        }
    ).sort_values("abs_coef", ascending=False)
    coef_df.to_csv(LINEAR_SEPARATOR_COEFS_PATH, index=False)

    # Predictions for all posts in split (train + test)
    pred_rows = []
    for split_name, ids, idx, y_true, y_hat, y_p in (
        ("train", train_ids, train_idx, y_train, train_pred, train_prob),
        ("test", test_ids, test_idx, y_test, test_pred, test_prob),
    ):
        labels = meta["label"].to_numpy()[idx]
        is_correct = meta["is_correct"].to_numpy()[idx]
        for i, pid in enumerate(ids):
            pred_rows.append(
                {
                    "post_id": pid,
                    "split": split_name,
                    "label": int(labels[i]),
                    "is_correct": int(is_correct[i]),
                    "is_error": int(y_true[i]),
                    "y_pred_error": int(y_hat[i]),
                    "y_prob_error": float(y_p[i]),
                }
            )
    pd.DataFrame(pred_rows).to_csv(LINEAR_SEPARATOR_PREDS_PATH, index=False)

    # Final metrics write (artifacts confirmed on disk)
    write_metrics_partial(metrics)

    print(
        f"TEST  accuracy={test_metrics['accuracy']:.4f} "
        f"roc_auc={test_metrics['roc_auc']:.4f} "
        f"pr_auc={test_metrics['pr_auc']:.4f} "
        f"f1_error={test_metrics['f1_error']:.4f}"
    )
    print(
        f"TRAIN accuracy={train_metrics['accuracy']:.4f} "
        f"roc_auc={train_metrics['roc_auc']:.4f} "
        f"pr_auc={train_metrics['pr_auc']:.4f}"
    )
    print(f"Wrote {LINEAR_SEPARATOR_METRICS_PATH}")
    print(f"Wrote {LOGISTIC_METRICS_PATH} (alias)")
    print(f"Wrote {LINEAR_SEPARATOR_MODEL_PATH}")
    print(f"Wrote {LINEAR_SEPARATOR_COEFS_PATH}")
    print(f"Wrote {LINEAR_SEPARATOR_PREDS_PATH}")

    append_train_progress(
        [
            f"## {_utc_now()} — metrics",
            "",
            f"- **Test** accuracy={test_metrics['accuracy']:.4f} "
            f"roc_auc={test_metrics['roc_auc']:.4f} "
            f"pr_auc={test_metrics['pr_auc']:.4f} "
            f"precision_error={test_metrics['precision_error']:.4f} "
            f"recall_error={test_metrics['recall_error']:.4f} "
            f"f1_error={test_metrics['f1_error']:.4f}",
            f"- **Train** accuracy={train_metrics['accuracy']:.4f} "
            f"roc_auc={train_metrics['roc_auc']:.4f} "
            f"pr_auc={train_metrics['pr_auc']:.4f}",
            f"- Confusion (test, error=1): tn={test_metrics['confusion_matrix']['tn']} "
            f"fp={test_metrics['confusion_matrix']['fp']} "
            f"fn={test_metrics['confusion_matrix']['fn']} "
            f"tp={test_metrics['confusion_matrix']['tp']}",
            "",
            f"## {_utc_now()} — artifact paths",
            "",
            f"- `{LINEAR_SEPARATOR_METRICS_PATH}`",
            f"- `{LOGISTIC_METRICS_PATH}` (alias)",
            f"- `{LINEAR_SEPARATOR_MODEL_PATH}`",
            f"- `{LINEAR_SEPARATOR_COEFS_PATH}`",
            f"- `{LINEAR_SEPARATOR_PREDS_PATH}`",
            f"- Progress: `{PROGRESS_UPDATES_TRAIN_PATH}`",
            "",
            "- Status: **complete** (no Bedrock calls; used existing shared split only)",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
