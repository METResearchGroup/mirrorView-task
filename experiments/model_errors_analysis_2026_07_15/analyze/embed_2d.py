"""Leakage-safe PCA / LDA 2D visualization of right vs wrong.

Loads the shared ``split_ids.json`` (does **not** re-split). Fits StandardScaler,
PCA(2), and LDA on **train only**, then transforms train+test.

Run from repo root::

    PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    ANALYSIS_META_PATH,
    EMBEDDING_MATRIX_PATH,
    EMBEDDINGS_2D_PATH,
    FEATURE_SET,
    LDA_PLOT_PATH,
    PCA_PLOT_PATH,
    PRIMARY_CLASSIFIER_ID,
    PROGRESS_UPDATES_VIZ_PATH,
    REDUCTION_SUMMARY_PATH,
    SPLIT_IDS_PATH,
    ANALYSIS_DIR,
)

RNG = np.random.default_rng(42)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip()


def append_viz_progress(lines: list[str]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PROGRESS_UPDATES_VIZ_PATH.is_file():
        existing = PROGRESS_UPDATES_VIZ_PATH.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    PROGRESS_UPDATES_VIZ_PATH.write_text(existing + block, encoding="utf-8")


def load_inputs() -> tuple[np.ndarray, pd.DataFrame, dict, np.ndarray, np.ndarray]:
    if not EMBEDDING_MATRIX_PATH.is_file():
        raise FileNotFoundError(f"Missing {EMBEDDING_MATRIX_PATH}")
    if not ANALYSIS_META_PATH.is_file():
        raise FileNotFoundError(f"Missing {ANALYSIS_META_PATH}")
    if not SPLIT_IDS_PATH.is_file():
        raise FileNotFoundError(f"Missing {SPLIT_IDS_PATH} — run split.py first")

    X = np.load(EMBEDDING_MATRIX_PATH)
    meta = pd.read_csv(ANALYSIS_META_PATH)
    split = json.loads(SPLIT_IDS_PATH.read_text(encoding="utf-8"))

    meta = meta.copy()
    meta["post_id"] = meta["post_id"].astype(str)
    meta["is_correct"] = meta["is_correct"].astype(int)
    meta["is_error"] = meta["is_error"].astype(int)
    meta["label"] = meta["label"].astype(int)

    if len(meta) != len(X):
        raise ValueError(f"Row mismatch: meta={len(meta)} X={X.shape}")
    if meta["post_id"].duplicated().any():
        raise ValueError("Duplicate post_id in analysis_meta")

    train_ids = [str(x) for x in split["train_post_ids"]]
    test_ids = [str(x) for x in split["test_post_ids"]]
    train_set, test_set = set(train_ids), set(test_ids)
    all_ids = set(meta["post_id"])

    if train_set & test_set:
        raise AssertionError("split_ids has train/test overlap — refuse to proceed")
    if train_set | test_set != all_ids:
        raise AssertionError("split_ids does not cover analysis_meta post_ids")
    if split.get("feature_set") not in (None, FEATURE_SET):
        raise ValueError(f"Unexpected feature_set in split: {split.get('feature_set')}")
    if split.get("classifier_id") not in (None, PRIMARY_CLASSIFIER_ID):
        raise ValueError(f"Unexpected classifier_id in split: {split.get('classifier_id')}")

    train_mask = meta["post_id"].isin(train_set).to_numpy()
    test_mask = meta["post_id"].isin(test_set).to_numpy()
    if int(train_mask.sum()) != len(train_ids) or int(test_mask.sum()) != len(test_ids):
        raise AssertionError("train/test mask counts do not match split_ids lengths")

    return X, meta, split, train_mask, test_mask


def fit_reductions(
    X: np.ndarray,
    y_error: np.ndarray,
    train_mask: np.ndarray,
) -> tuple[StandardScaler, PCA, LinearDiscriminantAnalysis, PCA, dict]:
    """Fit scaler/PCA/LDA on train only. LDA is 1D for binary; residual PCA → 2nd axis."""
    scaler = StandardScaler()
    scaler.fit(X[train_mask])
    Xs = scaler.transform(X)

    pca = PCA(n_components=2, random_state=42)
    pca.fit(Xs[train_mask])

    # Binary LDA → at most 1 discriminant (n_classes - 1).
    lda = LinearDiscriminantAnalysis(n_components=1)
    lda.fit(Xs[train_mask], y_error[train_mask])

    # Second axis for LDA scatter: first PC of residuals orthogonal to LDA direction.
    # scalings_ is (n_features, n_components) in the space LDA was fit on (standardized).
    w = np.asarray(lda.scalings_[:, 0], dtype=float)
    w = w / (np.linalg.norm(w) + 1e-12)
    proj = Xs @ w
    residual = Xs - np.outer(proj, w)
    pca_orth = PCA(n_components=1, random_state=42)
    pca_orth.fit(residual[train_mask])

    info = {
        "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "pca_explained_variance_ratio_cumsum": np.cumsum(pca.explained_variance_ratio_).tolist(),
        "pca_singular_values": pca.singular_values_.tolist(),
        "lda_n_components": 1,
        "lda_classes": lda.classes_.tolist(),
        "lda_explained_variance_ratio": (
            lda.explained_variance_ratio_.tolist()
            if getattr(lda, "explained_variance_ratio_", None) is not None
            else None
        ),
        "lda_orthogonal_pc1_explained_variance_ratio": float(
            pca_orth.explained_variance_ratio_[0]
        ),
    }
    return scaler, pca, lda, pca_orth, info


def transform_all(
    X: np.ndarray,
    scaler: StandardScaler,
    pca: PCA,
    lda: LinearDiscriminantAnalysis,
    pca_orth: PCA,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    Xs = scaler.transform(X)
    Z_pca = pca.transform(Xs)
    Z_ld1 = lda.transform(Xs).ravel()

    w = np.asarray(lda.scalings_[:, 0], dtype=float)
    w = w / (np.linalg.norm(w) + 1e-12)
    residual = Xs - np.outer(Xs @ w, w)
    Z_orth = pca_orth.transform(residual).ravel()
    return Z_pca, Z_ld1, Z_orth


def _correctness_colors(is_correct: np.ndarray) -> np.ndarray:
    # right=teal, wrong=coral
    palette = np.array(["#2A9D8F", "#E76F51"])
    return palette[1 - is_correct.astype(int)]


def plot_pca(
    Z_pca: np.ndarray,
    meta: pd.DataFrame,
    train_mask: np.ndarray,
    out_path: Path,
    *,
    explained: list[float],
) -> dict:
    """PCA scatter colored by right/wrong; markers distinguish train/test; optional 2D LR boundary."""
    is_correct = meta["is_correct"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharex=True, sharey=True)

    for ax, mask, title in (
        (axes[0], train_mask, "Train"),
        (axes[1], ~train_mask, "Test"),
    ):
        for correct, label, color, marker in (
            (1, "correct (right)", "#2A9D8F", "o"),
            (0, "wrong (error)", "#E76F51", "x"),
        ):
            m = mask & (is_correct == correct)
            ax.scatter(
                Z_pca[m, 0],
                Z_pca[m, 1],
                c=color,
                marker=marker,
                s=18 if correct else 28,
                alpha=0.55,
                linewidths=0.8 if correct == 0 else 0.0,
                label=label,
                rasterized=True,
            )
        ax.set_title(title)
        ax.set_xlabel(f"PC1 ({100 * explained[0]:.1f}% var)")
        ax.set_ylabel(f"PC2 ({100 * explained[1]:.1f}% var)")
        ax.axhline(0, color="#bbb", lw=0.6)
        ax.axvline(0, color="#bbb", lw=0.6)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    # 2D logistic boundary on PCA train coords (viz-only; not the 256-d linear separator).
    clf = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
    y_train = meta.loc[train_mask, "is_error"].to_numpy()
    clf.fit(Z_pca[train_mask], y_train)
    boundary_note = _draw_2d_logistic_boundary(axes[0], clf, Z_pca[train_mask])
    _draw_2d_logistic_boundary(axes[1], clf, Z_pca[~train_mask])

    fig.suptitle(
        "PCA (2D) of only_original Titan — Qwen3 Next 80B right vs wrong\n"
        "Scaler+PCA fit on train only; boundary = 2D logistic on PC coords (train fit)",
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    # Alias requested in task brief
    alias = out_path.with_name("pca_scatter.png")
    fig.savefig(alias, dpi=160, bbox_inches="tight")
    plt.close(fig)

    # Quick separability diagnostics in PC plane
    train_acc = float(clf.score(Z_pca[train_mask], y_train))
    test_acc = float(
        clf.score(Z_pca[~train_mask], meta.loc[~train_mask, "is_error"].to_numpy())
    )
    return {
        "pca_2d_logistic_train_accuracy": train_acc,
        "pca_2d_logistic_test_accuracy": test_acc,
        "pca_2d_logistic_coef": clf.coef_.ravel().tolist(),
        "pca_2d_logistic_intercept": float(clf.intercept_[0]),
        "boundary_note": boundary_note,
        "alias_path": str(alias),
    }


def _draw_2d_logistic_boundary(ax, clf: LogisticRegression, Z: np.ndarray) -> str:
    """Draw decision boundary for 2-feature logistic in the axis data limits."""
    xmin, xmax = np.percentile(Z[:, 0], [1, 99])
    ymin, ymax = np.percentile(Z[:, 1], [1, 99])
    pad_x = 0.05 * (xmax - xmin + 1e-9)
    pad_y = 0.05 * (ymax - ymin + 1e-9)
    xx, yy = np.meshgrid(
        np.linspace(xmin - pad_x, xmax + pad_x, 200),
        np.linspace(ymin - pad_y, ymax + pad_y, 200),
    )
    grid = np.c_[xx.ravel(), yy.ravel()]
    zz = clf.predict_proba(grid)[:, 1].reshape(xx.shape)
    ax.contour(xx, yy, zz, levels=[0.5], colors=["#264653"], linewidths=1.4, linestyles="--")
    return "dashed contour = P(is_error)=0.5 from 2D logistic on PC1/PC2"


def plot_lda(
    Z_ld1: np.ndarray,
    Z_orth: np.ndarray,
    meta: pd.DataFrame,
    train_mask: np.ndarray,
    out_path: Path,
) -> dict:
    """Binary LDA: LD1 on x; residual PC1 on y (fit on train residuals)."""
    is_correct = meta["is_correct"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharex=True, sharey=True)

    for ax, mask, title in (
        (axes[0], train_mask, "Train"),
        (axes[1], ~train_mask, "Test"),
    ):
        for correct, label, color, marker in (
            (1, "correct (right)", "#2A9D8F", "o"),
            (0, "wrong (error)", "#E76F51", "x"),
        ):
            m = mask & (is_correct == correct)
            ax.scatter(
                Z_ld1[m],
                Z_orth[m],
                c=color,
                marker=marker,
                s=18 if correct else 28,
                alpha=0.55,
                linewidths=0.8 if correct == 0 else 0.0,
                label=label,
                rasterized=True,
            )
        # Class means on LD1
        for correct, color in ((1, "#2A9D8F"), (0, "#E76F51")):
            m = mask & (is_correct == correct)
            if m.any():
                ax.axvline(float(Z_ld1[m].mean()), color=color, lw=1.0, alpha=0.85, ls=":")
        ax.set_title(title)
        ax.set_xlabel("LD1 (fit on train; target=is_error)")
        ax.set_ylabel("Residual PC1 ⊥ LD1 (train-fit)")
        ax.axhline(0, color="#bbb", lw=0.6)
        ax.axvline(0, color="#bbb", lw=0.6)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    fig.suptitle(
        "LDA view of only_original Titan — Qwen3 Next 80B right vs wrong\n"
        "Binary LDA → 1 discriminant; y-axis = first PC of residuals orthogonal to LD1",
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    alias = out_path.with_name("lda_scatter.png")
    fig.savefig(alias, dpi=160, bbox_inches="tight")
    plt.close(fig)

    # Separability along LD1: mean difference / pooled std (Cohen-ish) on test
    def _sep(mask: np.ndarray) -> dict:
        right = Z_ld1[mask & (is_correct == 1)]
        wrong = Z_ld1[mask & (is_correct == 0)]
        if len(right) == 0 or len(wrong) == 0:
            return {"n_right": int(len(right)), "n_wrong": int(len(wrong))}
        mu_r, mu_w = float(right.mean()), float(wrong.mean())
        # pooled std
        n_r, n_w = len(right), len(wrong)
        var_p = ((n_r - 1) * right.var(ddof=1) + (n_w - 1) * wrong.var(ddof=1)) / max(
            n_r + n_w - 2, 1
        )
        d = (mu_w - mu_r) / (np.sqrt(var_p) + 1e-12)
        # threshold midway between means → crude accuracy
        thr = 0.5 * (mu_r + mu_w)
        # decide which side is "error": sign of (mu_w - mu_r)
        if mu_w >= mu_r:
            pred_error = Z_ld1[mask] >= thr
        else:
            pred_error = Z_ld1[mask] <= thr
        y_true = meta.loc[mask, "is_error"].to_numpy().astype(bool)
        acc = float((pred_error == y_true).mean())
        return {
            "n_right": int(n_r),
            "n_wrong": int(n_w),
            "mean_ld1_correct": mu_r,
            "mean_ld1_wrong": mu_w,
            "cohen_d_wrong_minus_correct": float(d),
            "midpoint_threshold_accuracy": acc,
        }

    return {
        "train_ld1_separability": _sep(train_mask),
        "test_ld1_separability": _sep(~train_mask),
        "alias_path": str(alias),
    }


def build_embeddings_2d_csv(
    meta: pd.DataFrame,
    train_mask: np.ndarray,
    Z_pca: np.ndarray,
    Z_ld1: np.ndarray,
    Z_orth: np.ndarray,
    out_path: Path,
) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "post_id": meta["post_id"].astype(str),
            "pc1": Z_pca[:, 0],
            "pc2": Z_pca[:, 1],
            "ld1": Z_ld1,
            "lda_orth_pc1": Z_orth,
            "split": np.where(train_mask, "train", "test"),
            "is_correct": meta["is_correct"].astype(int),
            "is_error": meta["is_error"].astype(int),
            "label": meta["label"].astype(int),
        }
    )
    out.to_csv(out_path, index=False)
    return out


def main() -> int:
    append_viz_progress(
        [
            f"## {_now()} — 2D reduction start",
            "",
            f"- Loading `{EMBEDDING_MATRIX_PATH.name}`, `{ANALYSIS_META_PATH.name}`, `{SPLIT_IDS_PATH.name}`",
            "- No re-split; no Bedrock; no 256-d logistic (linear separator owns that).",
            "",
        ]
    )

    X, meta, split, train_mask, test_mask = load_inputs()
    y_error = meta["is_error"].to_numpy()
    print(
        f"Loaded X={X.shape} n_train={train_mask.sum()} n_test={test_mask.sum()} "
        f"seed={split.get('seed')} err_rate={y_error.mean():.4f}"
    )

    append_viz_progress(
        [
            f"## {_now()} — fit reductions (train only)",
            "",
            f"- n_train={int(train_mask.sum())} n_test={int(test_mask.sum())} dim={X.shape[1]}",
            "- StandardScaler → PCA(2) → LDA(1) + residual PCA(1) for LDA y-axis",
            "",
        ]
    )

    scaler, pca, lda, pca_orth, red_info = fit_reductions(X, y_error, train_mask)
    Z_pca, Z_ld1, Z_orth = transform_all(X, scaler, pca, lda, pca_orth)

    print(
        "PCA var explained:",
        [f"{100 * v:.2f}%" for v in red_info["pca_explained_variance_ratio"]],
    )

    pca_extra = plot_pca(
        Z_pca,
        meta,
        train_mask,
        PCA_PLOT_PATH,
        explained=red_info["pca_explained_variance_ratio"],
    )
    print(f"Wrote {PCA_PLOT_PATH} (+ {pca_extra['alias_path']})")

    lda_extra = plot_lda(Z_ld1, Z_orth, meta, train_mask, LDA_PLOT_PATH)
    print(f"Wrote {LDA_PLOT_PATH} (+ {lda_extra['alias_path']})")

    emb_df = build_embeddings_2d_csv(meta, train_mask, Z_pca, Z_ld1, Z_orth, EMBEDDINGS_2D_PATH)
    print(f"Wrote {EMBEDDINGS_2D_PATH} rows={len(emb_df)}")

    summary = {
        "classifier_id": PRIMARY_CLASSIFIER_ID,
        "feature_set": FEATURE_SET,
        "split_path": str(SPLIT_IDS_PATH),
        "seed": split.get("seed"),
        "n_train": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
        "fit_on": "train_only",
        "transform": "train_and_test",
        "pca": {
            "n_components": 2,
            "explained_variance_ratio": red_info["pca_explained_variance_ratio"],
            "explained_variance_ratio_cumsum": red_info["pca_explained_variance_ratio_cumsum"],
            "singular_values": red_info["pca_singular_values"],
        },
        "lda": {
            "n_components": 1,
            "note": "Binary classification → max 1 discriminant; y-axis is residual PC1 ⊥ LD1",
            "explained_variance_ratio": red_info["lda_explained_variance_ratio"],
            "orthogonal_pc1_explained_variance_ratio": red_info[
                "lda_orthogonal_pc1_explained_variance_ratio"
            ],
            "train_ld1_separability": lda_extra["train_ld1_separability"],
            "test_ld1_separability": lda_extra["test_ld1_separability"],
        },
        "pca_2d_logistic_overlay": {
            "train_accuracy": pca_extra["pca_2d_logistic_train_accuracy"],
            "test_accuracy": pca_extra["pca_2d_logistic_test_accuracy"],
            "coef_pc1_pc2": pca_extra["pca_2d_logistic_coef"],
            "intercept": pca_extra["pca_2d_logistic_intercept"],
            "note": pca_extra["boundary_note"],
        },
        "artifacts": {
            "pca_right_vs_wrong_png": str(PCA_PLOT_PATH),
            "lda_right_vs_wrong_png": str(LDA_PLOT_PATH),
            "pca_scatter_png": pca_extra["alias_path"],
            "lda_scatter_png": lda_extra["alias_path"],
            "embeddings_2d_csv": str(EMBEDDINGS_2D_PATH),
        },
    }
    REDUCTION_SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    # Also write a short variance-only alias
    var_path = ANALYSIS_DIR / "pca_variance_explained.json"
    var_path.write_text(
        json.dumps(
            {
                "explained_variance_ratio": red_info["pca_explained_variance_ratio"],
                "explained_variance_ratio_cumsum": red_info[
                    "pca_explained_variance_ratio_cumsum"
                ],
                "fit_on": "train_only",
                "n_components": 2,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {REDUCTION_SUMMARY_PATH}")
    print(f"Wrote {var_path}")

    test_sep = lda_extra["test_ld1_separability"]
    append_viz_progress(
        [
            f"## {_now()} — artifacts written",
            "",
            f"- PCA plot: `{PCA_PLOT_PATH.name}` / `pca_scatter.png`",
            f"- LDA plot: `{LDA_PLOT_PATH.name}` / `lda_scatter.png`",
            f"- Coords: `{EMBEDDINGS_2D_PATH.name}` ({len(emb_df)} rows)",
            f"- Summary: `{REDUCTION_SUMMARY_PATH.name}`, `pca_variance_explained.json`",
            f"- PCA var: "
            + ", ".join(f"PC{i+1}={100*v:.2f}%" for i, v in enumerate(red_info["pca_explained_variance_ratio"]))
            + f" (cumsum={100*red_info['pca_explained_variance_ratio_cumsum'][-1]:.2f}%)",
            f"- PCA-plane 2D-logistic test acc (viz overlay only): "
            f"{pca_extra['pca_2d_logistic_test_accuracy']:.3f}",
            f"- LDA test LD1 Cohen-d (wrong−correct): "
            f"{test_sep.get('cohen_d_wrong_minus_correct', float('nan')):.3f}; "
            f"midpoint thr acc={test_sep.get('midpoint_threshold_accuracy', float('nan')):.3f}",
            "",
            "### Visual separability (brief)",
            "",
            "- PCA: first two PCs capture limited variance of 256-d Titan; right/wrong clouds "
            "are heavily overlapping in the PC plane (see test 2D-logistic acc near chance if low).",
            "- LDA: supervised 1D projection maximizes class separation on **train**; test "
            "Cohen-d / midpoint accuracy indicate how much of that linear structure holds out-of-sample.",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
