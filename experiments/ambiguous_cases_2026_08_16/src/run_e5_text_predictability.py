"""Predict ambiguity and labels from text features (E5).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e5_text_predictability.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from shared.textual_features.char_count import CharCountMetric
from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric
from shared.textual_features.punctuation_density import PunctuationDensityMetric
from shared.textual_features.reading_ease import FleschReadingEaseMetric
from shared.textual_features.word_count import WordCountMetric

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
E2_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "post_effects.csv"
METRICS_JSON = EXPERIMENT_ROOT / "outputs" / "e5" / "metrics.json"
FEATURE_IMPORTANCE_CSV = EXPERIMENT_ROOT / "outputs" / "e5" / "feature_importance.csv"
GREY_ZONE_CSV = EXPERIMENT_ROOT / "outputs" / "e5" / "grey_zone_contrast.csv"

_EMBED_DIR = (
    Path(__file__).resolve().parents[2]
    / "bertopic_modeling_2026_08_05"
    / "outputs"
    / "embeddings"
    / "original"
)
_PRIOR_FEATURES_CSV = (
    Path(__file__).resolve().parents[2]
    / "unanimous_vs_majority_labels_2026_08_08"
    / "outputs"
    / "analysis1"
    / "per_post_features.csv"
)
_SEED = 42
_SURFACE_NAMES = [
    "char_count",
    "word_count",
    "punctuation_density",
    "flesch_kincaid_grade",
    "flesch_reading_ease",
]


def _compute_surface_features(texts: pd.Series) -> pd.DataFrame:
    """Compute deterministic surface metrics for each text."""
    metrics = [
        CharCountMetric(),
        WordCountMetric(),
        PunctuationDensityMetric(),
        FleschKincaidGradeMetric(),
        FleschReadingEaseMetric(),
    ]
    rows = []
    for text in texts.astype(str):
        row = {}
        for metric in metrics:
            row[metric.name] = float(metric.calculate(text))
        rows.append(row)
    return pd.DataFrame(rows)


def _load_embeddings() -> tuple[np.ndarray, pd.DataFrame]:
    """Load Titan embeddings and their index."""
    embeddings = np.load(_EMBED_DIR / "embeddings.npy")
    index = pd.read_parquet(_EMBED_DIR / "index.parquet")
    if "message_id" not in index.columns:
        raise KeyError("Embedding index missing message_id")
    index = index.copy()
    index["message_id"] = index["message_id"].astype(str)
    return embeddings, index


def run_e5() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Train text models and write E5 outputs."""
    posts = pd.read_csv(POST_FRAME_CSV)
    effects = pd.read_csv(E2_EFFECTS_CSV)
    frame = posts.merge(effects, on="post_id", how="inner")
    embeddings, index = _load_embeddings()
    index = index.reset_index(drop=True)
    index["embed_row"] = np.arange(len(index))
    frame = frame.merge(
        index[["message_id", "embed_row"]],
        left_on="post_id",
        right_on="message_id",
        how="inner",
    )
    surface = _compute_surface_features(frame["original_text"])
    for col in surface.columns:
        frame[col] = surface[col].to_numpy()

    prior = pd.read_csv(_PRIOR_FEATURES_CSV)
    prior["message_id"] = prior["message_id"].astype(str)
    frame = frame.merge(
        prior[["message_id", "is_positive", "is_intergroup", "is_prime"]],
        on="message_id",
        how="left",
    )

    x_embed = embeddings[frame["embed_row"].to_numpy()]
    x_surface = frame[_SURFACE_NAMES].to_numpy(dtype=float)
    x_all = np.hstack([x_embed, x_surface])

    # Classification target excludes ties.
    class_frame = frame[~frame["is_tie"]].copy()
    y_label = (class_frame["remove_count"] > class_frame["keep_count"]).astype(int)
    x_label = x_all[~frame["is_tie"].to_numpy()]

    x_train, x_test, y_train, y_test = train_test_split(
        x_label,
        y_label,
        test_size=0.2,
        random_state=_SEED,
        stratify=y_label,
    )
    scaler_label = StandardScaler()
    x_train_s = scaler_label.fit_transform(x_train)
    x_test_s = scaler_label.transform(x_test)
    label_model = LogisticRegression(
        max_iter=2000, random_state=_SEED, solver="lbfgs"
    )
    label_model.fit(x_train_s, y_train)
    label_pred = label_model.predict(x_test_s)
    label_proba = label_model.predict_proba(x_test_s)[:, 1]
    label_acc = float(accuracy_score(y_test, label_pred))
    label_auc = float(roc_auc_score(y_test, label_proba))

    # Ambiguity regression includes ties.
    y_amb = frame["adjusted_ambiguity_score"].to_numpy(dtype=float)
    x_amb_train, x_amb_test, y_amb_train, y_amb_test = train_test_split(
        x_all, y_amb, test_size=0.2, random_state=_SEED
    )
    scaler_amb = StandardScaler()
    x_amb_train_s = scaler_amb.fit_transform(x_amb_train)
    x_amb_test_s = scaler_amb.transform(x_amb_test)
    amb_model = Ridge(alpha=1.0, random_state=_SEED)
    amb_model.fit(x_amb_train_s, y_amb_train)
    amb_pred = amb_model.predict(x_amb_test_s)
    amb_r2 = float(r2_score(y_amb_test, amb_pred))
    amb_r = float(np.corrcoef(y_amb_test, amb_pred)[0, 1])

    # One/two-rater label check using modal labels from all trials.
    trials = pd.read_csv(TRIAL_FRAME_CSV)
    small = (
        trials.groupby("post_id")
        .agg(
            n_raters=("decision", "size"),
            remove_count=("is_remove", "sum"),
            original_text=("original_text", "first"),
        )
        .reset_index()
    )
    small = small[small["n_raters"].isin([1, 2])].copy()
    small = small.merge(
        index[["message_id", "embed_row"]],
        left_on="post_id",
        right_on="message_id",
        how="inner",
    )
    if len(small):
        small_surface = _compute_surface_features(small["original_text"])
        x_small = np.hstack(
            [
                embeddings[small["embed_row"].to_numpy()],
                small_surface[_SURFACE_NAMES].to_numpy(dtype=float),
            ]
        )
        y_small = (small["remove_count"] > (small["n_raters"] / 2)).astype(int)
        # For n=1, remove_count > 0.5 means remove; for n=2 ties excluded by >
        small_pred = label_model.predict(scaler_label.transform(x_small))
        small_acc = float(accuracy_score(y_small, small_pred))
        n_small = int(len(small))
    else:
        small_acc = float("nan")
        n_small = 0

    # Feature importance: surface coef magnitudes for both models.
    n_embed = x_embed.shape[1]
    label_surface_coef = np.abs(label_model.coef_.ravel()[n_embed:])
    amb_surface_coef = np.abs(amb_model.coef_[n_embed:])
    importance = pd.DataFrame(
        {
            "feature": _SURFACE_NAMES,
            "label_abs_coef": label_surface_coef,
            "ambiguity_abs_coef": amb_surface_coef,
        }
    )

    # Grey-zone contrast using reused classifier labels when present.
    labeled = frame.dropna(subset=["is_positive", "is_intergroup", "is_prime"]).copy()
    q_hi = labeled["adjusted_ambiguity_score"].quantile(0.75)
    q_lo = labeled["adjusted_ambiguity_score"].quantile(0.25)
    labeled["grey_flag"] = (
        ((labeled["is_prime"] == True) | (labeled["is_intergroup"] == True))  # noqa: E712
        & (labeled["is_positive"] == False)  # noqa: E712
    )
    top = labeled[labeled["adjusted_ambiguity_score"] >= q_hi]
    bot = labeled[labeled["adjusted_ambiguity_score"] <= q_lo]
    grey = pd.DataFrame(
        [
            {
                "group": "top_ambiguity_quartile",
                "n": int(len(top)),
                "n_grey_flag": int(top["grey_flag"].sum()),
                "share_grey_flag": float(top["grey_flag"].mean()) if len(top) else float("nan"),
            },
            {
                "group": "bottom_ambiguity_quartile",
                "n": int(len(bot)),
                "n_grey_flag": int(bot["grey_flag"].sum()),
                "share_grey_flag": float(bot["grey_flag"].mean()) if len(bot) else float("nan"),
            },
        ]
    )

    metrics = {
        "label_test_accuracy": label_acc,
        "label_test_roc_auc": label_auc,
        "ambiguity_test_r2": amb_r2,
        "ambiguity_test_pearson_r": amb_r,
        "n_train": int(len(x_train)),
        "n_test": int(len(x_test)),
        "n_one_or_two_rater_label_check": n_small,
        "one_or_two_rater_label_accuracy": small_acc,
        "seed": _SEED,
        "n_posts_with_embeddings": int(len(frame)),
    }

    METRICS_JSON.parent.mkdir(parents=True, exist_ok=True)
    METRICS_JSON.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    importance.to_csv(FEATURE_IMPORTANCE_CSV, index=False)
    grey.to_csv(GREY_ZONE_CSV, index=False)
    return metrics, importance, grey


def main() -> None:
    """CLI entry for E5."""
    metrics, importance, grey = run_e5()
    print(f"Wrote {METRICS_JSON}")
    print(f"Wrote {FEATURE_IMPORTANCE_CSV}")
    print(f"Wrote {GREY_ZONE_CSV}")
    print(f"ambiguity_test_pearson_r {metrics['ambiguity_test_pearson_r']:.6f}")
    print(f"label_test_roc_auc {metrics['label_test_roc_auc']:.6f}")
    print(f"n_importance_rows {len(importance)}")
    print(f"n_grey_rows {len(grey)}")


if __name__ == "__main__":
    main()
