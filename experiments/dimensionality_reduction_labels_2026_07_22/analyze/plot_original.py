"""PCA/LDA single-scatter for original-post Titan embeddings vs human keep/remove.

Run from root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/plot_original.py
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
    FEATURE_SET_ORIGINAL,
    FIT_REGIME,
    ORIGINAL_DIR,
    X_ORIGINAL_PATH,
)
from analyze.reduction import (  # noqa: E402
    fit_reductions,
    load_meta,
    plot_lda_single,
    plot_pca_single,
    transform_all,
)


def main() -> int:
    if not X_ORIGINAL_PATH.is_file():
        raise FileNotFoundError(f"Missing {X_ORIGINAL_PATH} — run build_table.py first")

    X = np.load(X_ORIGINAL_PATH)
    meta = load_meta()
    if len(meta) != X.shape[0]:
        raise ValueError(f"Row mismatch: meta={len(meta)} X={X.shape}")

    y = meta["label"].to_numpy()
    print(f"Loaded X_original={X.shape} keep={int((y == 0).sum())} remove={int((y == 1).sum())}")

    scaler, pca, lda, pca_orth, red_info = fit_reductions(X, y)
    Z_pca, Z_ld1, Z_orth = transform_all(X, scaler, pca, lda, pca_orth)

    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    pca_path = ORIGINAL_DIR / "pca_remove_vs_keep.png"
    lda_path = ORIGINAL_DIR / "lda_remove_vs_keep.png"

    pca_extra = plot_pca_single(
        Z_pca,
        y,
        pca_path,
        title="PCA (2D) of original Titan — human remove vs keep",
        explained=red_info["pca_explained_variance_ratio"],
    )
    lda_extra = plot_lda_single(
        Z_ld1,
        Z_orth,
        y,
        lda_path,
        title="LDA view of original Titan — human remove vs keep",
    )

    emb = pd.DataFrame(
        {
            "post_id": meta["post_id"].astype(str),
            "pc1": Z_pca[:, 0],
            "pc2": Z_pca[:, 1],
            "ld1": Z_ld1,
            "lda_orth_pc1": Z_orth,
            "label": y.astype(int),
        }
    )
    emb_path = ORIGINAL_DIR / "embeddings_2d.csv"
    emb.to_csv(emb_path, index=False)

    summary = {
        "feature_set": FEATURE_SET_ORIGINAL,
        "fit_regime": FIT_REGIME,
        "n_rows": int(X.shape[0]),
        "embedding_dim": int(X.shape[1]),
        "pca": {
            "n_components": 2,
            "explained_variance_ratio": red_info["pca_explained_variance_ratio"],
            "explained_variance_ratio_cumsum": red_info["pca_explained_variance_ratio_cumsum"],
        },
        "lda": {
            "n_components": 1,
            "classes": red_info["lda_classes"],
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
    summary_path = ORIGINAL_DIR / "reduction_summary.json"
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
