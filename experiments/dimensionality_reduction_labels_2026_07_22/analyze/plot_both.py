"""PCA/LDA single-scatter for stacked original+mirrored Titan vs human keep/remove.

Block stack order: ``X_stack = vstack([X_original, X_mirrored])`` with parallel
``post_id`` / ``label`` / ``text_role`` arrays of length 2N (original block then
mirrored block). Binary LDA/PCA target remains human ``label`` (linked fate);
role is encoded only via darker (original) / lighter (mirrored) colors.

Run from root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/plot_both.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    BOTH_DIR,
    FEATURE_SET_BOTH,
    FIT_REGIME,
    X_MIRRORED_PATH,
    X_ORIGINAL_PATH,
)
from analyze.reduction import (  # noqa: E402
    fit_reductions,
    load_meta,
    plot_lda_both,
    plot_pca_both,
    transform_all,
)


def main() -> int:
    for path in (X_ORIGINAL_PATH, X_MIRRORED_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path} — run build_table.py first")

    X_orig = np.load(X_ORIGINAL_PATH)
    X_mir = np.load(X_MIRRORED_PATH)
    meta = load_meta()
    if len(meta) != X_orig.shape[0] or X_orig.shape != X_mir.shape:
        raise ValueError(
            f"Shape mismatch: meta={len(meta)} X_orig={X_orig.shape} X_mir={X_mir.shape}"
        )

    n = len(meta)
    X = np.vstack([X_orig, X_mir])
    y = np.concatenate([meta["label"].to_numpy(), meta["label"].to_numpy()])
    post_ids = np.concatenate(
        [meta["post_id"].astype(str).to_numpy(), meta["post_id"].astype(str).to_numpy()]
    )
    text_role = np.array(["original"] * n + ["mirrored"] * n)

    print(
        f"Stacked X={X.shape} (2×{n}) keep={int((y == 0).sum())} remove={int((y == 1).sum())}"
    )

    scaler, pca, lda, pca_orth, red_info = fit_reductions(X, y)
    Z_pca, Z_ld1, Z_orth = transform_all(X, scaler, pca, lda, pca_orth)

    BOTH_DIR.mkdir(parents=True, exist_ok=True)
    pca_path = BOTH_DIR / "pca_remove_vs_keep.png"
    lda_path = BOTH_DIR / "lda_remove_vs_keep.png"

    pca_extra = plot_pca_both(
        Z_pca,
        y,
        text_role,
        pca_path,
        title=(
            "PCA (2D) of original+mirrored Titan — human remove vs keep "
            "(dark=original, light=mirrored)"
        ),
        explained=red_info["pca_explained_variance_ratio"],
    )
    lda_extra = plot_lda_both(
        Z_ld1,
        Z_orth,
        y,
        text_role,
        lda_path,
        title=(
            "LDA view of original+mirrored Titan — human remove vs keep "
            "(dark=original, light=mirrored)"
        ),
    )

    emb = pd.DataFrame(
        {
            "post_id": post_ids,
            "text_role": text_role,
            "pc1": Z_pca[:, 0],
            "pc2": Z_pca[:, 1],
            "ld1": Z_ld1,
            "lda_orth_pc1": Z_orth,
            "label": y.astype(int),
        }
    )
    emb_path = BOTH_DIR / "embeddings_2d.csv"
    emb.to_csv(emb_path, index=False)

    summary = {
        "feature_set": FEATURE_SET_BOTH,
        "fit_regime": FIT_REGIME,
        "n_posts": int(n),
        "n_rows": int(X.shape[0]),
        "stack_order": "block_[X_original; X_mirrored]",
        "embedding_dim": int(X.shape[1]),
        "pca": {
            "n_components": 2,
            "explained_variance_ratio": red_info["pca_explained_variance_ratio"],
            "explained_variance_ratio_cumsum": red_info["pca_explained_variance_ratio_cumsum"],
        },
        "lda": {
            "n_components": 1,
            "classes": red_info["lda_classes"],
            "note": "Binary label LDA; text_role is plot-only (darker/lighter), not an LDA class",
            "orthogonal_pc1_explained_variance_ratio": red_info[
                "lda_orthogonal_pc1_explained_variance_ratio"
            ],
            "ld1_separability_full_data": lda_extra["ld1_separability"],
        },
        "pca_2d_logistic_overlay": pca_extra,
        "artifacts": {
            "pca_png": str(pca_path),
            "lda_png": str(lda_path),
            "embeddings_2d_csv": str(emb_path),
        },
    }
    summary_path = BOTH_DIR / "reduction_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {pca_path}")
    print(f"Wrote {lda_path}")
    print(f"Wrote {emb_path} rows={len(emb)}")
    print(f"Wrote {summary_path}")
    print(
        "PCA var:",
        [f"{100 * v:.2f}%" for v in red_info["pca_explained_variance_ratio"]],
        "LD1 Cohen-d (remove−keep):",
        lda_extra["ld1_separability"].get("cohen_d_remove_minus_keep"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
