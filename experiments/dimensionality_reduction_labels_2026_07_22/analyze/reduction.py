"""Full-data PCA/LDA helpers + single-scatter plot primitives for keep/remove viz.

Exploratory fit: StandardScaler / PCA / LDA are fit on **all** rows (no train mask).
Coloring targets human ``label`` (0=keep, 1=remove), not model correctness.

Run helpers are imported by ``plot_original.py``, ``plot_mirrored.py``, ``plot_both.py``.
"""

from __future__ import annotations

import sys
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

from analyze.paths import ANALYSIS_META_PATH  # noqa: E402

COLORS = {
    "keep": "#2E7D32",
    "remove": "#C62828",
    "keep_original": "#1B5E20",
    "remove_original": "#B71C1C",
    "keep_mirrored": "#81C784",
    "remove_mirrored": "#EF9A9A",
}


def load_meta() -> pd.DataFrame:
    """Load ``analysis_meta.csv`` aligned to X row order."""
    if not ANALYSIS_META_PATH.is_file():
        raise FileNotFoundError(f"Missing {ANALYSIS_META_PATH}")
    meta = pd.read_csv(ANALYSIS_META_PATH)
    required = {"post_id", "label"}
    missing = required - set(meta.columns)
    if missing:
        raise KeyError(f"analysis_meta missing columns: {sorted(missing)}")
    meta = meta.copy()
    meta["post_id"] = meta["post_id"].astype(str)
    meta["label"] = meta["label"].astype(int)
    if meta["post_id"].duplicated().any():
        raise ValueError("Duplicate post_id in analysis_meta")
    return meta


def fit_reductions(
    X: np.ndarray,
    y_label: np.ndarray,
) -> tuple[StandardScaler, PCA, LinearDiscriminantAnalysis, PCA, dict]:
    """Fit scaler/PCA/LDA on **all** rows. LDA is 1D for binary; residual PCA → 2nd axis."""
    y = np.asarray(y_label).astype(int)
    classes = set(np.unique(y).tolist())
    if classes != {0, 1}:
        raise ValueError(f"LDA expects label classes {{0, 1}}; got {sorted(classes)}")

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    pca = PCA(n_components=2, random_state=42)
    pca.fit(Xs)

    lda = LinearDiscriminantAnalysis(n_components=1)
    lda.fit(Xs, y)

    w = np.asarray(lda.scalings_[:, 0], dtype=float)
    w = w / (np.linalg.norm(w) + 1e-12)
    proj = Xs @ w
    residual = Xs - np.outer(proj, w)
    pca_orth = PCA(n_components=1, random_state=42)
    pca_orth.fit(residual)

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
        "fit_regime": "full_data_exploratory",
        "n_rows_fit": int(X.shape[0]),
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


def _draw_2d_logistic_boundary(ax, clf: LogisticRegression, Z: np.ndarray) -> str:
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
    return "dashed contour = P(remove)=0.5 from 2D logistic on PC1/PC2 (full-data fit)"


def cohen_d_remove_minus_keep(Z_ld1: np.ndarray, y_label: np.ndarray) -> dict:
    """Descriptive full-data LD1 Cohen-d (remove − keep). Not a holdout metric."""
    y = np.asarray(y_label).astype(int)
    keep = Z_ld1[y == 0]
    remove = Z_ld1[y == 1]
    if len(keep) == 0 or len(remove) == 0:
        return {"n_keep": int(len(keep)), "n_remove": int(len(remove))}
    mu_k, mu_r = float(keep.mean()), float(remove.mean())
    n_k, n_r = len(keep), len(remove)
    var_p = ((n_k - 1) * keep.var(ddof=1) + (n_r - 1) * remove.var(ddof=1)) / max(n_k + n_r - 2, 1)
    d = (mu_r - mu_k) / (np.sqrt(var_p) + 1e-12)
    return {
        "n_keep": int(n_k),
        "n_remove": int(n_r),
        "mean_ld1_keep": mu_k,
        "mean_ld1_remove": mu_r,
        "cohen_d_remove_minus_keep": float(d),
    }


def plot_pca_single(
    Z_pca: np.ndarray,
    y_label: np.ndarray,
    out_path: Path,
    *,
    title: str,
    explained: list[float],
    draw_boundary: bool = True,
) -> dict:
    """Single-axes PCA scatter colored by keep/remove."""
    y = np.asarray(y_label).astype(int)
    fig, ax = plt.subplots(1, 1, figsize=(7.2, 6.0))

    for lab, name, color, marker in (
        (0, "keep", COLORS["keep"], "o"),
        (1, "remove", COLORS["remove"], "x"),
    ):
        m = y == lab
        ax.scatter(
            Z_pca[m, 0],
            Z_pca[m, 1],
            c=color,
            marker=marker,
            s=18 if lab == 0 else 28,
            alpha=0.55,
            linewidths=0.8 if lab == 1 else 0.0,
            label=name,
            rasterized=True,
        )

    ax.set_xlabel(f"PC1 ({100 * explained[0]:.1f}% var)")
    ax.set_ylabel(f"PC2 ({100 * explained[1]:.1f}% var)")
    ax.axhline(0, color="#bbb", lw=0.6)
    ax.axvline(0, color="#bbb", lw=0.6)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)

    overlay: dict = {}
    if draw_boundary:
        clf = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
        clf.fit(Z_pca, y)
        note = _draw_2d_logistic_boundary(ax, clf, Z_pca)
        overlay = {
            "pca_2d_logistic_accuracy": float(clf.score(Z_pca, y)),
            "pca_2d_logistic_coef": clf.coef_.ravel().tolist(),
            "pca_2d_logistic_intercept": float(clf.intercept_[0]),
            "boundary_note": note,
        }

    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return overlay


def plot_lda_single(
    Z_ld1: np.ndarray,
    Z_orth: np.ndarray,
    y_label: np.ndarray,
    out_path: Path,
    *,
    title: str,
) -> dict:
    """Single-axes LDA scatter: LD1 on x; residual PC1 on y."""
    y = np.asarray(y_label).astype(int)
    fig, ax = plt.subplots(1, 1, figsize=(7.2, 6.0))

    for lab, name, color, marker in (
        (0, "keep", COLORS["keep"], "o"),
        (1, "remove", COLORS["remove"], "x"),
    ):
        m = y == lab
        ax.scatter(
            Z_ld1[m],
            Z_orth[m],
            c=color,
            marker=marker,
            s=18 if lab == 0 else 28,
            alpha=0.55,
            linewidths=0.8 if lab == 1 else 0.0,
            label=name,
            rasterized=True,
        )
        if m.any():
            ax.axvline(float(Z_ld1[m].mean()), color=color, lw=1.0, alpha=0.85, ls=":")

    ax.set_xlabel("LD1 (full-data fit; target=label keep/remove)")
    ax.set_ylabel("Residual PC1 ⊥ LD1 (full-data fit)")
    ax.axhline(0, color="#bbb", lw=0.6)
    ax.axvline(0, color="#bbb", lw=0.6)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return {"ld1_separability": cohen_d_remove_minus_keep(Z_ld1, y)}


def plot_pca_both(
    Z_pca: np.ndarray,
    y_label: np.ndarray,
    text_role: np.ndarray,
    out_path: Path,
    *,
    title: str,
    explained: list[float],
) -> dict:
    """Single-axes PCA with dark=original / light=mirrored keep/remove palette."""
    y = np.asarray(y_label).astype(int)
    roles = np.asarray(text_role)
    fig, ax = plt.subplots(1, 1, figsize=(8.0, 6.2))

    series = (
        (0, "original", "keep (original)", COLORS["keep_original"], "o"),
        (1, "original", "remove (original)", COLORS["remove_original"], "x"),
        (0, "mirrored", "keep (mirrored)", COLORS["keep_mirrored"], "o"),
        (1, "mirrored", "remove (mirrored)", COLORS["remove_mirrored"], "x"),
    )
    for lab, role, name, color, marker in series:
        m = (y == lab) & (roles == role)
        ax.scatter(
            Z_pca[m, 0],
            Z_pca[m, 1],
            c=color,
            marker=marker,
            s=18 if lab == 0 else 28,
            alpha=0.55,
            linewidths=0.8 if lab == 1 else 0.0,
            label=name,
            rasterized=True,
        )

    ax.set_xlabel(f"PC1 ({100 * explained[0]:.1f}% var)")
    ax.set_ylabel(f"PC2 ({100 * explained[1]:.1f}% var)")
    ax.axhline(0, color="#bbb", lw=0.6)
    ax.axvline(0, color="#bbb", lw=0.6)
    ax.legend(loc="best", fontsize=8, framealpha=0.9)

    clf = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
    clf.fit(Z_pca, y)
    note = _draw_2d_logistic_boundary(ax, clf, Z_pca)

    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return {
        "pca_2d_logistic_accuracy": float(clf.score(Z_pca, y)),
        "pca_2d_logistic_coef": clf.coef_.ravel().tolist(),
        "pca_2d_logistic_intercept": float(clf.intercept_[0]),
        "boundary_note": note,
    }


def plot_lda_both(
    Z_ld1: np.ndarray,
    Z_orth: np.ndarray,
    y_label: np.ndarray,
    text_role: np.ndarray,
    out_path: Path,
    *,
    title: str,
) -> dict:
    """Single-axes LDA with dark=original / light=mirrored keep/remove palette."""
    y = np.asarray(y_label).astype(int)
    roles = np.asarray(text_role)
    fig, ax = plt.subplots(1, 1, figsize=(8.0, 6.2))

    series = (
        (0, "original", "keep (original)", COLORS["keep_original"], "o"),
        (1, "original", "remove (original)", COLORS["remove_original"], "x"),
        (0, "mirrored", "keep (mirrored)", COLORS["keep_mirrored"], "o"),
        (1, "mirrored", "remove (mirrored)", COLORS["remove_mirrored"], "x"),
    )
    for lab, role, name, color, marker in series:
        m = (y == lab) & (roles == role)
        ax.scatter(
            Z_ld1[m],
            Z_orth[m],
            c=color,
            marker=marker,
            s=18 if lab == 0 else 28,
            alpha=0.55,
            linewidths=0.8 if lab == 1 else 0.0,
            label=name,
            rasterized=True,
        )

    for lab, color in ((0, COLORS["keep"]), (1, COLORS["remove"])):
        m = y == lab
        if m.any():
            ax.axvline(float(Z_ld1[m].mean()), color=color, lw=1.0, alpha=0.85, ls=":")

    ax.set_xlabel("LD1 (full-data fit; target=label keep/remove)")
    ax.set_ylabel("Residual PC1 ⊥ LD1 (full-data fit)")
    ax.axhline(0, color="#bbb", lw=0.6)
    ax.axvline(0, color="#bbb", lw=0.6)
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return {"ld1_separability": cohen_d_remove_minus_keep(Z_ld1, y)}
