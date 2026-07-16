"""V1.4 — Reduced-space clustering of Qwen right/wrong in Titan only_original.

Loads the shared ``split_ids.json`` (does **not** re-split). Fits StandardScaler
+ PCA on **train only**, selects k-means ``k`` via train silhouette (k=5..15),
assigns test via ``predict``, and reports per-cluster error rates / lift vs the
global ~36% base rate. Optional full-256d k-means sanity pass.

Run from repo root::

    PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_cluster.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    ANALYSIS_META_PATH,
    CLUSTER_ASSIGNMENTS_PATH,
    CLUSTER_EXEMPLARS_CSV_PATH,
    CLUSTER_EXEMPLARS_PATH,
    CLUSTER_K_SELECTION_PATH,
    CLUSTER_METRICS_CSV_PATH,
    CLUSTER_METRICS_JSON_PATH,
    CLUSTER_MODEL_PATH,
    CLUSTER_PLOT_PATH,
    CLUSTER_PROGRESS_PATH,
    CLUSTERS_DIR,
    EMBEDDING_DIM,
    EMBEDDING_MATRIX_PATH,
    FEATURE_SET,
    LABELS_CSV_PATH,
    PRIMARY_CLASSIFIER_ID,
    SPLIT_IDS_PATH,
    SPLIT_SEED,
)

# Clustering hyperparameters (locked for this investigation)
K_RANGE = range(5, 16)  # inclusive 5..15
PCA_VARIANCE_TARGET = 0.50  # choose enough PCs for ~50% train variance
PCA_N_MIN = 10
PCA_N_MAX = 20
PCA_N_VIZ = 2
STABILITY_SEEDS = (42, 0, 1, 7, 123)
MIN_TEST_N_FOR_FLAG = 15
LIFT_HIGH_THRESHOLD = 1.25  # error rate / global >= this → high-lift candidate
LIFT_LOW_THRESHOLD = 0.70  # near-zero / sparse error island candidate
STABLE_ABS_DELTA_MAX = 0.08  # |train_rate - test_rate| for "stable"
N_EXEMPLARS_PER_CLUSTER = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def append_progress(lines: list[str]) -> None:
    CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if CLUSTER_PROGRESS_PATH.is_file():
        existing = CLUSTER_PROGRESS_PATH.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    CLUSTER_PROGRESS_PATH.write_text(existing + block, encoding="utf-8")


def load_split_ids() -> dict[str, Any]:
    if not SPLIT_IDS_PATH.is_file():
        raise FileNotFoundError(
            f"Missing shared split {SPLIT_IDS_PATH}. Run v1_split.py first; "
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
    if not EMBEDDING_MATRIX_PATH.is_file():
        raise FileNotFoundError(f"Missing {EMBEDDING_MATRIX_PATH}")
    if not ANALYSIS_META_PATH.is_file():
        raise FileNotFoundError(f"Missing {ANALYSIS_META_PATH}")

    meta = pd.read_csv(ANALYSIS_META_PATH)
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
    id_to_idx = {pid: i for i, pid in enumerate(meta["post_id"].tolist())}
    missing = [pid for pid in post_ids if pid not in id_to_idx]
    if missing:
        raise KeyError(
            f"{len(missing)} post_ids from split missing in meta (e.g. {missing[:3]})"
        )
    return np.asarray([id_to_idx[pid] for pid in post_ids], dtype=np.int64)


def choose_n_components(explained_ratio: np.ndarray) -> int:
    """Pick PCA dim: first k with cumsum >= target, clipped to [PCA_N_MIN, PCA_N_MAX]."""
    cumsum = np.cumsum(explained_ratio)
    hit = int(np.searchsorted(cumsum, PCA_VARIANCE_TARGET) + 1)
    return int(np.clip(hit, PCA_N_MIN, PCA_N_MAX))


def select_k_silhouette(
    Z_train: np.ndarray,
    k_range: range = K_RANGE,
    seed: int = SPLIT_SEED,
) -> tuple[int, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    best_k = int(k_range.start)
    best_sil = -1.0
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=seed, n_init=10, max_iter=300)
        labels = km.fit_predict(Z_train)
        sil = float(silhouette_score(Z_train, labels, metric="euclidean", sample_size=min(4000, len(Z_train)), random_state=seed))
        inertia = float(km.inertia_)
        rows.append({"k": int(k), "silhouette": sil, "inertia": inertia})
        if sil > best_sil:
            best_sil = sil
            best_k = int(k)
    return best_k, rows


def cluster_stats(
    labels: np.ndarray,
    y_error: np.ndarray,
    split_name: str,
    global_rate: float,
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for cid in sorted(set(int(c) for c in labels)):
        m = labels == cid
        n = int(m.sum())
        n_err = int(y_error[m].sum()) if n else 0
        rate = float(n_err / n) if n else float("nan")
        lift = float(rate / global_rate) if n and global_rate > 0 else float("nan")
        out[cid] = {
            f"n_{split_name}": n,
            f"n_error_{split_name}": n_err,
            f"error_rate_{split_name}": rate,
            f"lift_{split_name}": lift,
        }
    return out


def stability_across_seeds(
    Z_train: np.ndarray,
    k: int,
    seeds: tuple[int, ...] = STABILITY_SEEDS,
) -> dict[str, Any]:
    """Pairwise adjusted Rand-ish agreement via label matching on train assignments."""
    from sklearn.metrics import adjusted_rand_score

    label_mats: list[np.ndarray] = []
    for s in seeds:
        km = KMeans(n_clusters=k, random_state=s, n_init=10, max_iter=300)
        label_mats.append(km.fit_predict(Z_train))

    aris: list[float] = []
    for i in range(len(label_mats)):
        for j in range(i + 1, len(label_mats)):
            aris.append(float(adjusted_rand_score(label_mats[i], label_mats[j])))

    # Per-seed global train error concentration: max cluster lift
    max_lifts: list[float] = []
    y = None  # filled by caller if needed — here we only report ARI
    return {
        "seeds": list(seeds),
        "pairwise_ari_mean": float(np.mean(aris)) if aris else None,
        "pairwise_ari_min": float(np.min(aris)) if aris else None,
        "pairwise_ari_max": float(np.max(aris)) if aris else None,
        "n_pairs": len(aris),
        "note": (
            "ARI across k-means seeds on train PCA coords; "
            "low ARI ⇒ assignment sensitive to seed"
        ),
        "max_lifts_placeholder": max_lifts,
        "y_unused": y,
    }


def flag_cluster(row: dict[str, Any], global_rate: float) -> list[str]:
    flags: list[str] = []
    n_test = int(row.get("n_test", 0))
    train_rate = float(row["error_rate_train"])
    test_rate = float(row["error_rate_test"]) if n_test else float("nan")
    train_lift = float(row["lift_train"])
    test_lift = float(row["lift_test"]) if n_test else float("nan")
    abs_delta = abs(train_rate - test_rate) if n_test else float("nan")

    stable = n_test >= MIN_TEST_N_FOR_FLAG and abs_delta <= STABLE_ABS_DELTA_MAX
    if n_test >= MIN_TEST_N_FOR_FLAG and train_lift >= LIFT_HIGH_THRESHOLD and test_lift >= LIFT_HIGH_THRESHOLD and stable:
        flags.append("high_lift_stable")
    elif n_test >= MIN_TEST_N_FOR_FLAG and train_lift >= LIFT_HIGH_THRESHOLD and test_lift >= LIFT_HIGH_THRESHOLD:
        flags.append("high_lift_unstable")
    if n_test >= MIN_TEST_N_FOR_FLAG and train_lift <= LIFT_LOW_THRESHOLD and test_lift <= LIFT_LOW_THRESHOLD and stable:
        flags.append("low_error_island_stable")
    elif n_test >= MIN_TEST_N_FOR_FLAG and train_lift <= LIFT_LOW_THRESHOLD and test_lift <= LIFT_LOW_THRESHOLD:
        flags.append("low_error_island_unstable")
    if n_test < MIN_TEST_N_FOR_FLAG:
        flags.append("small_test")
    _ = global_rate  # used implicitly via lifts already computed
    return flags


def full_256d_sanity(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    k: int,
    global_rate: float,
    seed: int = SPLIT_SEED,
) -> dict[str, Any]:
    """Cheap sanity: k-means in scaled full 256-d with same k as PCA path."""
    scaler = StandardScaler()
    Xt = scaler.fit_transform(X_train)
    Xte = scaler.transform(X_test)
    km = KMeans(n_clusters=k, random_state=seed, n_init=10, max_iter=300)
    lab_tr = km.fit_predict(Xt)
    lab_te = km.predict(Xte)
    sil = float(
        silhouette_score(
            Xt,
            lab_tr,
            metric="euclidean",
            sample_size=min(4000, len(Xt)),
            random_state=seed,
        )
    )
    rows = []
    for cid in range(k):
        m_tr = lab_tr == cid
        m_te = lab_te == cid
        n_tr, n_te = int(m_tr.sum()), int(m_te.sum())
        r_tr = float(y_train[m_tr].mean()) if n_tr else float("nan")
        r_te = float(y_test[m_te].mean()) if n_te else float("nan")
        rows.append(
            {
                "cluster_id": cid,
                "n_train": n_tr,
                "n_test": n_te,
                "error_rate_train": r_tr,
                "error_rate_test": r_te,
                "lift_train": float(r_tr / global_rate) if n_tr and global_rate else None,
                "lift_test": float(r_te / global_rate) if n_te and global_rate else None,
            }
        )
    lifts_test = [r["lift_test"] for r in rows if r["lift_test"] is not None and r["n_test"] >= MIN_TEST_N_FOR_FLAG]
    return {
        "space": "scaled_256d",
        "k": k,
        "train_silhouette": sil,
        "clusters": rows,
        "max_test_lift": float(max(lifts_test)) if lifts_test else None,
        "min_test_lift": float(min(lifts_test)) if lifts_test else None,
    }


def plot_pca2d_clusters(
    Z2: np.ndarray,
    cluster_ids: np.ndarray,
    is_error: np.ndarray,
    train_mask: np.ndarray,
    lift_table: pd.DataFrame,
    out_path: Path,
    *,
    explained: list[float],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.4), sharex=True, sharey=True)
    cmap = plt.get_cmap("tab20")
    k = int(cluster_ids.max()) + 1

    for ax, mask, title in (
        (axes[0], train_mask, "Train"),
        (axes[1], ~train_mask, "Test"),
    ):
        for cid in range(k):
            m = mask & (cluster_ids == cid)
            if not m.any():
                continue
            ax.scatter(
                Z2[m, 0],
                Z2[m, 1],
                c=[cmap(cid % 20)],
                s=14,
                alpha=0.45,
                label=f"c{cid}",
                rasterized=True,
            )
            # annotate cluster centroid with test/train error rate
            row = lift_table.loc[lift_table["cluster_id"] == cid]
            if len(row):
                rate_col = "error_rate_train" if title == "Train" else "error_rate_test"
                rate = float(row.iloc[0][rate_col])
                ax.annotate(
                    f"c{cid}\n{100 * rate:.0f}%",
                    (float(Z2[m, 0].mean()), float(Z2[m, 1].mean())),
                    fontsize=7,
                    ha="center",
                    va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888", alpha=0.85),
                )
        ax.set_title(title)
        ax.set_xlabel(f"PC1 ({100 * explained[0]:.1f}% var)")
        ax.set_ylabel(f"PC2 ({100 * explained[1]:.1f}% var)")
        ax.axhline(0, color="#bbb", lw=0.5)
        ax.axvline(0, color="#bbb", lw=0.5)

    # small error overlay legend
    axes[1].scatter([], [], c="#E76F51", marker="x", s=40, label="(error markers in exemplars)")
    fig.suptitle(
        "PCA (2D) colored by train-fit k-means clusters — Qwen error rates annotated\n"
        "Scaler+PCA+k-means fit on train only; test assigned via predict",
        fontsize=11,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    _ = is_error  # available for future overlays; rates shown via annotations


def write_exemplars(
    lift_table: pd.DataFrame,
    assignments: pd.DataFrame,
    labels_csv: Path,
    md_path: Path,
    csv_path: Path,
    n_per: int = N_EXEMPLARS_PER_CLUSTER,
) -> list[int]:
    interesting = lift_table[
        lift_table["flags"].str.contains("stable|high_lift|low_error", regex=True, na=False)
    ].copy()
    if interesting.empty:
        # fall back to extreme train lifts for qualitative peek
        interesting = lift_table.sort_values("lift_train", ascending=False).head(3)
        interesting = pd.concat(
            [interesting, lift_table.sort_values("lift_train", ascending=True).head(2)]
        ).drop_duplicates("cluster_id")

    texts = pd.read_csv(labels_csv)
    texts["post_id"] = texts["post_id"].astype(str)
    texts = texts[["post_id", "original_text", "mirrored_text"]].copy()

    # assignments already has label / is_error / is_correct; only join texts
    merged = assignments.merge(texts, on="post_id", how="left")
    exemplar_rows: list[dict[str, Any]] = []
    lines = [
        f"# Cluster exemplars ({_utc_now()})",
        "",
        "Spot-check posts from interesting / extreme clusters. Texts from "
        f"`{labels_csv.name}` (Qwen primary run). Truncated for readability.",
        "",
    ]

    for _, crow in interesting.iterrows():
        cid = int(crow["cluster_id"])
        lines.append(f"## Cluster {cid}")
        lines.append("")
        lines.append(
            f"- train n={int(crow['n_train'])} rate={crow['error_rate_train']:.3f} "
            f"lift={crow['lift_train']:.2f}"
        )
        lines.append(
            f"- test n={int(crow['n_test'])} rate={crow['error_rate_test']:.3f} "
            f"lift={crow['lift_test']:.2f}"
        )
        lines.append(f"- flags: `{crow['flags']}`")
        lines.append("")
        sub = merged[merged["cluster_id"] == cid].copy()
        # prefer errors for high-lift, correct for low-error islands
        if "high_lift" in str(crow["flags"]) or crow["lift_train"] >= 1.1:
            sub = sub.sort_values(["is_error", "split"], ascending=[False, True])
        else:
            sub = sub.sort_values(["is_error", "split"], ascending=[True, True])
        sample = sub.head(n_per)
        for i, (_, r) in enumerate(sample.iterrows(), start=1):
            orig = str(r.get("original_text", ""))[:400]
            mir = str(r.get("mirrored_text", ""))[:400]
            lines.append(
                f"{i}. `post_id={r['post_id']}` split={r['split']} "
                f"is_error={int(r['is_error'])} label={int(r['label'])}"
            )
            lines.append(f"   - original: {orig}")
            lines.append(f"   - mirrored: {mir}")
            lines.append("")
            exemplar_rows.append(
                {
                    "cluster_id": cid,
                    "post_id": r["post_id"],
                    "split": r["split"],
                    "is_error": int(r["is_error"]),
                    "label": int(r["label"]),
                    "original_text": r.get("original_text"),
                    "mirrored_text": r.get("mirrored_text"),
                    "flags": crow["flags"],
                }
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(exemplar_rows).to_csv(csv_path, index=False)
    return [int(x) for x in interesting["cluster_id"].tolist()]


def main() -> int:
    CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
    append_progress(
        [
            f"## {_utc_now()} — V1.4 cluster investigation start",
            "",
            f"- Shared split: `{SPLIT_IDS_PATH}` (no re-split)",
            f"- Features: `{EMBEDDING_MATRIX_PATH}`",
            "- No Bedrock calls.",
            "",
        ]
    )

    split = load_split_ids()
    meta, X = load_xy()
    train_ids = [str(x) for x in split["train_post_ids"]]
    test_ids = [str(x) for x in split["test_post_ids"]]

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
    y = meta["is_error"].to_numpy()
    y_train, y_test = y[train_idx], y[test_idx]
    X_train, X_test = X[train_idx], X[test_idx]
    global_rate = float(y.mean())
    train_rate = float(y_train.mean())
    test_rate = float(y_test.mean())

    print(
        f"Loaded X={X.shape} train={len(train_idx)} test={len(test_idx)} "
        f"global_err={global_rate:.4f}"
    )

    # --- Leakage-safe scaler + PCA (train fit) ---
    scaler = StandardScaler()
    Xs_train = scaler.fit_transform(X_train)
    Xs_test = scaler.transform(X_test)

    pca_full = PCA(n_components=PCA_N_MAX, random_state=SPLIT_SEED)
    pca_full.fit(Xs_train)
    n_comp = choose_n_components(pca_full.explained_variance_ratio_)
    pca = PCA(n_components=n_comp, random_state=SPLIT_SEED)
    Z_train = pca.fit_transform(Xs_train)
    Z_test = pca.transform(Xs_test)
    var_cumsum = float(np.sum(pca.explained_variance_ratio_))

    # 2D for viz continuity
    pca2 = PCA(n_components=PCA_N_VIZ, random_state=SPLIT_SEED)
    Z2_train = pca2.fit_transform(Xs_train)
    Z2_test = pca2.transform(Xs_test)
    Z2_all = np.zeros((len(meta), 2), dtype=float)
    Z2_all[train_idx] = Z2_train
    Z2_all[test_idx] = Z2_test

    append_progress(
        [
            f"## {_utc_now()} — PCA fit (train only)",
            "",
            f"- n_components={n_comp} (target cumvar>={PCA_VARIANCE_TARGET}, "
            f"clip [{PCA_N_MIN},{PCA_N_MAX}])",
            f"- cum explained variance (train)={var_cumsum:.4f}",
            f"- PC1/PC2 for viz: {[float(x) for x in pca2.explained_variance_ratio_]}",
            "",
        ]
    )
    print(f"PCA n_components={n_comp} cumvar={var_cumsum:.4f}")

    # --- k selection via silhouette on train ---
    best_k, k_rows = select_k_silhouette(Z_train, K_RANGE, SPLIT_SEED)
    k_sel_payload = {
        "method": "silhouette_on_train_pca",
        "k_range": [int(K_RANGE.start), int(K_RANGE.stop - 1)],
        "selected_k": best_k,
        "rows": k_rows,
        "pca_n_components": n_comp,
        "pca_cum_variance": var_cumsum,
    }
    CLUSTER_K_SELECTION_PATH.write_text(
        json.dumps(k_sel_payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Selected k={best_k} (best train silhouette)")
    append_progress(
        [
            f"## {_utc_now()} — k selection",
            "",
            f"- k range={list(K_RANGE)}; selected_k={best_k}",
            f"- silhouette@k: "
            + ", ".join(f"k={r['k']}:{r['silhouette']:.4f}" for r in k_rows),
            "",
        ]
    )

    # --- Fit primary k-means ---
    km = KMeans(n_clusters=best_k, random_state=SPLIT_SEED, n_init=10, max_iter=300)
    lab_train = km.fit_predict(Z_train)
    lab_test = km.predict(Z_test)
    train_sil = float(
        silhouette_score(
            Z_train,
            lab_train,
            metric="euclidean",
            sample_size=min(4000, len(Z_train)),
            random_state=SPLIT_SEED,
        )
    )

    stability = stability_across_seeds(Z_train, best_k, STABILITY_SEEDS)
    # drop unused placeholders
    stability.pop("max_lifts_placeholder", None)
    stability.pop("y_unused", None)

    # --- Per-cluster metrics ---
    train_stats = cluster_stats(lab_train, y_train, "train", global_rate)
    test_stats = cluster_stats(lab_test, y_test, "test", global_rate)

    rows: list[dict[str, Any]] = []
    for cid in range(best_k):
        row: dict[str, Any] = {"cluster_id": cid}
        row.update(train_stats.get(cid, {
            "n_train": 0,
            "n_error_train": 0,
            "error_rate_train": float("nan"),
            "lift_train": float("nan"),
        }))
        row.update(test_stats.get(cid, {
            "n_test": 0,
            "n_error_test": 0,
            "error_rate_test": float("nan"),
            "lift_test": float("nan"),
        }))
        row["abs_delta_rate"] = abs(
            float(row["error_rate_train"]) - float(row["error_rate_test"])
        ) if row["n_test"] else float("nan")
        row["flags"] = "|".join(flag_cluster(row, global_rate)) or "none"
        rows.append(row)

    lift_df = pd.DataFrame(rows).sort_values("cluster_id")
    lift_df.to_csv(CLUSTER_METRICS_CSV_PATH, index=False)

    # Decision gate
    stable_high = lift_df["flags"].str.contains("high_lift_stable", na=False)
    stable_low = lift_df["flags"].str.contains("low_error_island_stable", na=False)
    n_stable_interesting = int(stable_high.sum() + stable_low.sum())
    decision = (
        "local_structure"
        if n_stable_interesting > 0
        else "diffuse"
    )
    decision_note = (
        f"Found {int(stable_high.sum())} stable high-lift and "
        f"{int(stable_low.sum())} stable low-error clusters "
        f"(min test n={MIN_TEST_N_FOR_FLAG}, |Δrate|<={STABLE_ABS_DELTA_MAX}, "
        f"lift high>={LIFT_HIGH_THRESHOLD} / low<={LIFT_LOW_THRESHOLD})."
        if n_stable_interesting
        else (
            "No cluster with stable test enrichment or sparse-error island "
            f"(criteria: test n>={MIN_TEST_N_FOR_FLAG}, |train−test rate|<="
            f"{STABLE_ABS_DELTA_MAX}, lift>={LIFT_HIGH_THRESHOLD} or <="
            f"{LIFT_LOW_THRESHOLD}). Conclude errors are diffuse in Titan PCA space."
        )
    )

    # Assignments for all posts
    cluster_all = np.full(len(meta), -1, dtype=int)
    cluster_all[train_idx] = lab_train
    cluster_all[test_idx] = lab_test
    split_col = np.array(["train"] * len(meta), dtype=object)
    split_col[test_idx] = "test"

    assign_df = pd.DataFrame(
        {
            "post_id": meta["post_id"].astype(str),
            "split": split_col,
            "cluster_id": cluster_all,
            "is_error": meta["is_error"].astype(int),
            "is_correct": meta["is_correct"].astype(int),
            "label": meta["label"].astype(int),
            "pc1": Z2_all[:, 0],
            "pc2": Z2_all[:, 1],
        }
    )
    # add PCA-k coords for train/test
    for j in range(n_comp):
        col = np.full(len(meta), np.nan)
        col[train_idx] = Z_train[:, j]
        col[test_idx] = Z_test[:, j]
        assign_df[f"pca_{j}"] = col
    assign_df.to_csv(CLUSTER_ASSIGNMENTS_PATH, index=False)

    # Plot
    train_mask = np.zeros(len(meta), dtype=bool)
    train_mask[train_idx] = True
    plot_pca2d_clusters(
        Z2_all,
        cluster_all,
        meta["is_error"].to_numpy(),
        train_mask,
        lift_df,
        CLUSTER_PLOT_PATH,
        explained=pca2.explained_variance_ratio_.tolist(),
    )

    # Exemplars
    interesting_ids = write_exemplars(
        lift_df,
        assign_df,
        LABELS_CSV_PATH,
        CLUSTER_EXEMPLARS_PATH,
        CLUSTER_EXEMPLARS_CSV_PATH,
    )

    # Full-256d sanity
    print("Running full-256d k-means sanity...")
    sanity = full_256d_sanity(
        X_train, X_test, y_train, y_test, best_k, global_rate, SPLIT_SEED
    )

    # Persist model
    joblib.dump(
        {
            "scaler": scaler,
            "pca": pca,
            "pca2": pca2,
            "kmeans": km,
            "n_components": n_comp,
            "k": best_k,
            "feature_set": FEATURE_SET,
            "classifier_id": PRIMARY_CLASSIFIER_ID,
            "split_path": str(SPLIT_IDS_PATH),
            "seed": SPLIT_SEED,
        },
        CLUSTER_MODEL_PATH,
    )

    metrics: dict[str, Any] = {
        "status": "complete",
        "updated_at": _utc_now(),
        "classifier_id": PRIMARY_CLASSIFIER_ID,
        "feature_set": FEATURE_SET,
        "target": "is_error",
        "global_error_rate": global_rate,
        "train_error_rate": train_rate,
        "test_error_rate": test_rate,
        "split": {
            "path": str(SPLIT_IDS_PATH),
            "seed": split.get("seed"),
            "train_split": split.get("train_split"),
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "re_split": False,
        },
        "pca": {
            "n_components": n_comp,
            "variance_target": PCA_VARIANCE_TARGET,
            "n_min": PCA_N_MIN,
            "n_max": PCA_N_MAX,
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "explained_variance_ratio_cumsum": float(var_cumsum),
            "pca2_explained_variance_ratio": pca2.explained_variance_ratio_.tolist(),
            "fit_on": "train_only",
        },
        "kmeans": {
            "k": best_k,
            "k_selection": "train_silhouette",
            "train_silhouette": train_sil,
            "n_init": 10,
            "random_state": SPLIT_SEED,
            "stability": stability,
        },
        "thresholds": {
            "lift_high": LIFT_HIGH_THRESHOLD,
            "lift_low": LIFT_LOW_THRESHOLD,
            "stable_abs_delta_max": STABLE_ABS_DELTA_MAX,
            "min_test_n_for_flag": MIN_TEST_N_FOR_FLAG,
        },
        "clusters": rows,
        "summary": {
            "max_train_lift": float(lift_df["lift_train"].max()),
            "min_train_lift": float(lift_df["lift_train"].min()),
            "max_test_lift": float(lift_df.loc[lift_df["n_test"] >= MIN_TEST_N_FOR_FLAG, "lift_test"].max())
            if (lift_df["n_test"] >= MIN_TEST_N_FOR_FLAG).any()
            else None,
            "min_test_lift": float(lift_df.loc[lift_df["n_test"] >= MIN_TEST_N_FOR_FLAG, "lift_test"].min())
            if (lift_df["n_test"] >= MIN_TEST_N_FOR_FLAG).any()
            else None,
            "n_stable_high_lift": int(stable_high.sum()),
            "n_stable_low_error": int(stable_low.sum()),
            "interesting_cluster_ids": interesting_ids,
        },
        "decision_gate": {
            "verdict": decision,
            "note": decision_note,
        },
        "full_256d_sanity": sanity,
        "artifacts": {
            "assignments": str(CLUSTER_ASSIGNMENTS_PATH),
            "metrics_json": str(CLUSTER_METRICS_JSON_PATH),
            "metrics_csv": str(CLUSTER_METRICS_CSV_PATH),
            "k_selection": str(CLUSTER_K_SELECTION_PATH),
            "plot": str(CLUSTER_PLOT_PATH),
            "exemplars_md": str(CLUSTER_EXEMPLARS_PATH),
            "exemplars_csv": str(CLUSTER_EXEMPLARS_CSV_PATH),
            "model": str(CLUSTER_MODEL_PATH),
            "progress": str(CLUSTER_PROGRESS_PATH),
        },
    }
    CLUSTER_METRICS_JSON_PATH.write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"Decision gate: {decision} | "
        f"max_test_lift={metrics['summary']['max_test_lift']} "
        f"min_test_lift={metrics['summary']['min_test_lift']} "
        f"stable_high={int(stable_high.sum())} stable_low={int(stable_low.sum())}"
    )
    print(f"Wrote {CLUSTER_METRICS_JSON_PATH}")
    print(f"Wrote {CLUSTER_METRICS_CSV_PATH}")
    print(f"Wrote {CLUSTER_ASSIGNMENTS_PATH}")
    print(f"Wrote {CLUSTER_PLOT_PATH}")
    print(f"Wrote {CLUSTER_EXEMPLARS_PATH}")

    append_progress(
        [
            f"## {_utc_now()} — results",
            "",
            f"- selected_k={best_k} train_silhouette={train_sil:.4f}",
            f"- stability pairwise ARI mean={stability.get('pairwise_ari_mean')}",
            f"- max_test_lift={metrics['summary']['max_test_lift']} "
            f"min_test_lift={metrics['summary']['min_test_lift']}",
            f"- decision_gate **{decision}**: {decision_note}",
            f"- 256d sanity max_test_lift={sanity.get('max_test_lift')} "
            f"min_test_lift={sanity.get('min_test_lift')}",
            "",
            f"## {_utc_now()} — artifacts",
            "",
            f"- `{CLUSTER_ASSIGNMENTS_PATH}`",
            f"- `{CLUSTER_METRICS_JSON_PATH}`",
            f"- `{CLUSTER_METRICS_CSV_PATH}`",
            f"- `{CLUSTER_K_SELECTION_PATH}`",
            f"- `{CLUSTER_PLOT_PATH}`",
            f"- `{CLUSTER_EXEMPLARS_PATH}`",
            f"- `{CLUSTER_MODEL_PATH}`",
            "",
            "- Status: **complete** (no Bedrock; shared split only)",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
