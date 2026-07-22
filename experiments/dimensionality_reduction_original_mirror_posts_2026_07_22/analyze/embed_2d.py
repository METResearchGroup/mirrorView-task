"""Leakage-safe PCA / LDA 2D visualization of original vs mirrored posts.

Loads the shared ``split_ids.json`` (does **not** re-split). Fits StandardScaler,
PCA(2), and LDA on **train only** with target ``is_mirrored``, then transforms all.

Run from repo root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/embed_2d.py
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
    ANALYSIS_DIR,
    ANALYSIS_META_PATH,
    EMBEDDING_MATRIX_PATH,
    EMBEDDINGS_2D_PATH,
    FEATURE_SET,
    LDA_PLOT_PATH,
    LDA_TARGET,
    PCA_PLOT_PATH,
    PCA_VARIANCE_PATH,
    PROGRESS_UPDATES_VIZ_PATH,
    REDUCTION_SUMMARY_PATH,
    SPLIT_IDS_PATH,
)
from analyze.split_lib import assert_long_table_schema, expand_post_split_to_row_masks  # noqa: E402


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
        raise FileNotFoundError(
            f"Missing {SPLIT_IDS_PATH} — run split.py first"
        )

    X = np.load(EMBEDDING_MATRIX_PATH)
    meta = pd.read_csv(ANALYSIS_META_PATH)
    split = json.loads(SPLIT_IDS_PATH.read_text(encoding="utf-8"))

    meta = meta.copy()
    meta["post_id"] = meta["post_id"].astype(str)
    meta["text_role"] = meta["text_role"].astype(str)
    meta["is_mirrored"] = meta["is_mirrored"].astype(int)
    meta["label"] = meta["label"].astype(int)

    if len(meta) != len(X):
        raise ValueError(f"Row mismatch: meta={len(meta)} X={X.shape}")
    assert_long_table_schema(meta)

    # Allow duplicate post_id (exactly 2 each) — long matrix.
    counts = meta.groupby("post_id").size()
    if (counts != 2).any():
        raise ValueError("Expected exactly 2 rows per post_id in analysis_meta")

    train_ids = [str(x) for x in split["train_post_ids"]]
    test_ids = [str(x) for x in split["test_post_ids"]]
    train_mask_s, test_mask_s = expand_post_split_to_row_masks(meta, train_ids, test_ids)
    train_mask = train_mask_s.to_numpy()
    test_mask = test_mask_s.to_numpy()

    if split.get("feature_set") not in (None, FEATURE_SET):
        raise ValueError(f"Unexpected feature_set in split: {split.get('feature_set')}")
    if split.get("lda_target") not in (None, LDA_TARGET):
        raise ValueError(f"Unexpected lda_target in split: {split.get('lda_target')}")

    return X, meta, split, train_mask, test_mask


def fit_reductions(
    X: np.ndarray,
    y_mirrored: np.ndarray,
    train_mask: np.ndarray,
) -> tuple[StandardScaler, PCA, LinearDiscriminantAnalysis, PCA, dict]:
    """Fit scaler/PCA/LDA on train only. LDA is 1D for binary; residual PCA → 2nd axis."""
    scaler = StandardScaler()
    scaler.fit(X[train_mask])
    Xs = scaler.transform(X)

    pca = PCA(n_components=2, random_state=42)
    pca.fit(Xs[train_mask])

    lda = LinearDiscriminantAnalysis(n_components=1)
    lda.fit(Xs[train_mask], y_mirrored[train_mask])

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


def plot_pca(
    Z_pca: np.ndarray,
    meta: pd.DataFrame,
    train_mask: np.ndarray,
    out_path: Path,
    *,
    explained: list[float],
) -> dict:
    """PCA scatter colored by original vs mirrored; optional 2D LR boundary."""
    is_mirrored = meta["is_mirrored"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharex=True, sharey=True)

    for ax, mask, title in (
        (axes[0], train_mask, "Train"),
        (axes[1], ~train_mask, "Test"),
    ):
        for mirrored, label, color, marker in (
            (0, "original", "#2A9D8F", "o"),
            (1, "mirrored", "#E76F51", "x"),
        ):
            m = mask & (is_mirrored == mirrored)
            ax.scatter(
                Z_pca[m, 0],
                Z_pca[m, 1],
                c=color,
                marker=marker,
                s=18 if mirrored == 0 else 28,
                alpha=0.55,
                linewidths=0.8 if mirrored == 1 else 0.0,
                label=label,
                rasterized=True,
            )
        ax.set_title(title)
        ax.set_xlabel(f"PC1 ({100 * explained[0]:.1f}% var)")
        ax.set_ylabel(f"PC2 ({100 * explained[1]:.1f}% var)")
        ax.axhline(0, color="#bbb", lw=0.6)
        ax.axvline(0, color="#bbb", lw=0.6)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    clf = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
    y_train = meta.loc[train_mask, "is_mirrored"].to_numpy()
    clf.fit(Z_pca[train_mask], y_train)
    boundary_note = _draw_2d_logistic_boundary(axes[0], clf, Z_pca[train_mask])
    _draw_2d_logistic_boundary(axes[1], clf, Z_pca[~train_mask])

    fig.suptitle(
        "PCA (2D) of Titan original+mirror long matrix — original vs mirrored\n"
        "Scaler+PCA fit on train only; boundary = 2D logistic on PC coords (train fit)",
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    train_acc = float(clf.score(Z_pca[train_mask], y_train))
    test_acc = float(
        clf.score(Z_pca[~train_mask], meta.loc[~train_mask, "is_mirrored"].to_numpy())
    )
    return {
        "pca_2d_logistic_train_accuracy": train_acc,
        "pca_2d_logistic_test_accuracy": test_acc,
        "pca_2d_logistic_coef": clf.coef_.ravel().tolist(),
        "pca_2d_logistic_intercept": float(clf.intercept_[0]),
        "boundary_note": boundary_note,
    }


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
    return "dashed contour = P(is_mirrored)=0.5 from 2D logistic on PC1/PC2"


def plot_lda(
    Z_ld1: np.ndarray,
    Z_orth: np.ndarray,
    meta: pd.DataFrame,
    train_mask: np.ndarray,
    out_path: Path,
) -> dict:
    """Binary LDA: LD1 on x; residual PC1 on y (fit on train residuals)."""
    is_mirrored = meta["is_mirrored"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharex=True, sharey=True)

    for ax, mask, title in (
        (axes[0], train_mask, "Train"),
        (axes[1], ~train_mask, "Test"),
    ):
        for mirrored, label, color, marker in (
            (0, "original", "#2A9D8F", "o"),
            (1, "mirrored", "#E76F51", "x"),
        ):
            m = mask & (is_mirrored == mirrored)
            ax.scatter(
                Z_ld1[m],
                Z_orth[m],
                c=color,
                marker=marker,
                s=18 if mirrored == 0 else 28,
                alpha=0.55,
                linewidths=0.8 if mirrored == 1 else 0.0,
                label=label,
                rasterized=True,
            )
        for mirrored, color in ((0, "#2A9D8F"), (1, "#E76F51")):
            m = mask & (is_mirrored == mirrored)
            if m.any():
                ax.axvline(float(Z_ld1[m].mean()), color=color, lw=1.0, alpha=0.85, ls=":")
        ax.set_title(title)
        ax.set_xlabel("LD1 (fit on train; target=is_mirrored)")
        ax.set_ylabel("Residual PC1 ⊥ LD1 (train-fit)")
        ax.axhline(0, color="#bbb", lw=0.6)
        ax.axvline(0, color="#bbb", lw=0.6)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    fig.suptitle(
        "LDA view of Titan original+mirror long matrix — original vs mirrored\n"
        "Binary LDA → 1 discriminant; y-axis = first PC of residuals orthogonal to LD1",
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    def _sep(mask: np.ndarray) -> dict:
        original = Z_ld1[mask & (is_mirrored == 0)]
        mirrored = Z_ld1[mask & (is_mirrored == 1)]
        if len(original) == 0 or len(mirrored) == 0:
            return {"n_original": int(len(original)), "n_mirrored": int(len(mirrored))}
        mu_o, mu_m = float(original.mean()), float(mirrored.mean())
        n_o, n_m = len(original), len(mirrored)
        var_p = ((n_o - 1) * original.var(ddof=1) + (n_m - 1) * mirrored.var(ddof=1)) / max(
            n_o + n_m - 2, 1
        )
        d = (mu_m - mu_o) / (np.sqrt(var_p) + 1e-12)
        thr = 0.5 * (mu_o + mu_m)
        if mu_m >= mu_o:
            pred_mirrored = Z_ld1[mask] >= thr
        else:
            pred_mirrored = Z_ld1[mask] <= thr
        y_true = meta.loc[mask, "is_mirrored"].to_numpy().astype(bool)
        acc = float((pred_mirrored == y_true).mean())
        return {
            "n_original": int(n_o),
            "n_mirrored": int(n_m),
            "mean_ld1_original": mu_o,
            "mean_ld1_mirrored": mu_m,
            "cohen_d_mirrored_minus_original": float(d),
            "midpoint_threshold_accuracy": acc,
        }

    return {
        "train_ld1_separability": _sep(train_mask),
        "test_ld1_separability": _sep(~train_mask),
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
            "text_role": meta["text_role"].astype(str),
            "is_mirrored": meta["is_mirrored"].astype(int),
            "pc1": Z_pca[:, 0],
            "pc2": Z_pca[:, 1],
            "ld1": Z_ld1,
            "lda_orth_pc1": Z_orth,
            "split": np.where(train_mask, "train", "test"),
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
            "- No re-split; no Bedrock; LDA target = is_mirrored.",
            "",
        ]
    )

    X, meta, split, train_mask, test_mask = load_inputs()
    y_mirrored = meta["is_mirrored"].to_numpy()
    print(
        f"Loaded X={X.shape} n_train_rows={train_mask.sum()} n_test_rows={test_mask.sum()} "
        f"seed={split.get('seed')} is_mirrored_rate={y_mirrored.mean():.4f}"
    )

    append_viz_progress(
        [
            f"## {_now()} — fit reductions (train only)",
            "",
            f"- n_train_rows={int(train_mask.sum())} n_test_rows={int(test_mask.sum())} dim={X.shape[1]}",
            "- StandardScaler → PCA(2) → LDA(1; y=is_mirrored) + residual PCA(1)",
            "",
        ]
    )

    scaler, pca, lda, pca_orth, red_info = fit_reductions(X, y_mirrored, train_mask)
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
    print(f"Wrote {PCA_PLOT_PATH}")

    lda_extra = plot_lda(Z_ld1, Z_orth, meta, train_mask, LDA_PLOT_PATH)
    print(f"Wrote {LDA_PLOT_PATH}")

    emb_df = build_embeddings_2d_csv(meta, train_mask, Z_pca, Z_ld1, Z_orth, EMBEDDINGS_2D_PATH)
    print(f"Wrote {EMBEDDINGS_2D_PATH} rows={len(emb_df)}")

    summary = {
        "feature_set": FEATURE_SET,
        "lda_target": LDA_TARGET,
        "split_path": str(SPLIT_IDS_PATH),
        "seed": split.get("seed"),
        "n_train_rows": int(train_mask.sum()),
        "n_test_rows": int(test_mask.sum()),
        "n_train_posts": int(split.get("n_train", train_mask.sum() // 2)),
        "n_test_posts": int(split.get("n_test", test_mask.sum() // 2)),
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
            "target": LDA_TARGET,
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
            "pca_original_vs_mirrored_png": str(PCA_PLOT_PATH),
            "lda_original_vs_mirrored_png": str(LDA_PLOT_PATH),
            "embeddings_2d_csv": str(EMBEDDINGS_2D_PATH),
        },
    }
    REDUCTION_SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    PCA_VARIANCE_PATH.write_text(
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
    print(f"Wrote {PCA_VARIANCE_PATH}")

    test_sep = lda_extra["test_ld1_separability"]
    append_viz_progress(
        [
            f"## {_now()} — artifacts written",
            "",
            f"- PCA plot: `{PCA_PLOT_PATH.name}`",
            f"- LDA plot: `{LDA_PLOT_PATH.name}`",
            f"- Coords: `{EMBEDDINGS_2D_PATH.name}` ({len(emb_df)} rows)",
            f"- Summary: `{REDUCTION_SUMMARY_PATH.name}`, `{PCA_VARIANCE_PATH.name}`",
            f"- PCA var: "
            + ", ".join(
                f"PC{i+1}={100*v:.2f}%"
                for i, v in enumerate(red_info["pca_explained_variance_ratio"])
            )
            + f" (cumsum={100*red_info['pca_explained_variance_ratio_cumsum'][-1]:.2f}%)",
            f"- PCA-plane 2D-logistic test acc (viz overlay only): "
            f"{pca_extra['pca_2d_logistic_test_accuracy']:.3f}",
            f"- LDA test LD1 Cohen-d (mirrored−original): "
            f"{test_sep.get('cohen_d_mirrored_minus_original', float('nan')):.3f}; "
            f"midpoint thr acc={test_sep.get('midpoint_threshold_accuracy', float('nan')):.3f}",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
