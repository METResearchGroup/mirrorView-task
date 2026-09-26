"""Run Part 3 BERTopic ablations A0 through A5 and the review sample export.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py \\
      --ablation all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a0_baselines import run_a0_naive
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a1_umap_seeds import run_a1_umap_seeds
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a2_min_cluster import run_a2_min_cluster
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a3_minilm import run_a3_minilm
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a4_design import run_a4_design_comparison
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a5_outliers import run_a5_outliers
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.review_samples import write_review
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.summary import append_summary_row

EXPERIMENT = "experiments/bertopic_original_mirror_part3_2026_09_24"


def _latest(directory: Path) -> Path:
    runs = sorted(path for path in directory.iterdir() if path.is_dir())
    if not runs:
        raise FileNotFoundError(f"no runs in {directory}")
    return runs[-1]


def _blank_row(ablation_id: str, run_ts: str, setting: str, value: str) -> dict:
    return {
        "ablation_id": ablation_id,
        "run_ts": run_ts,
        "setting_changed": setting,
        "setting_value": value,
        "n_topics": None,
        "n_noise": None,
        "noise_share": None,
        "ari_vs_production": None,
        "nmi_vs_production": None,
        "spearman_q5_keep_rate": None,
        "q2_pair_agreement": None,
        "q3_role_dominated_topics": None,
        "notes": "",
    }


def _production_topics(production_original: Path) -> list[int]:
    from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import original_corpus

    corpus = original_corpus()
    frame = pd.read_parquet(production_original / "assignments.parquet")
    frame = frame.loc[frame["text_role"] == "original"]
    by_id = {str(post_id): int(topic) for post_id, topic in zip(frame["post_id"], frame["topic"])}
    return [by_id[post_id] for post_id in corpus.post_ids]


def run_selected(ablation: str, seed: int, production_original: Path, production_joint: Path) -> None:
    """Run one ablation name, or every ablation when ``ablation`` is ``all``."""
    root = paths.ablations_dir()
    run_ts = paths.new_run_timestamp()
    mirror_run = _latest(paths.topics_dir("mirror"))
    assign_run = _latest(paths.assignments_dir())
    if ablation in {"all", "a0"}:
        metadata = run_a0_naive(root / "a0_naive" / run_ts, seed)
        row = _blank_row("a0_naive", run_ts, "kmeans_k", str(metadata["k_chosen"]))
        row["notes"] = metadata["k_chosen_justification"]
        append_summary_row(row)
        print("ablation=a0_naive done")
    if ablation in {"all", "a1"}:
        payload = run_a1_umap_seeds(root / "a1_umap_seeds" / run_ts, _production_topics(production_original))
        for seed_row in payload["seed_rows"]:
            row = _blank_row("a1_umap_seeds", run_ts, "umap_random_state", str(seed_row["seed"]))
            row["n_topics"] = seed_row["n_topics"]
            row["n_noise"] = seed_row["n_noise"]
            row["noise_share"] = seed_row["noise_share"]
            if seed_row["seed"] == 42:
                row["ari_vs_production"] = payload["ari_seed42_vs_production"]
            row["notes"] = f"pairwise_mean_ari={payload['pairwise_mean_ari']}"
            append_summary_row(row)
        print(f"ablation=a1_umap_seeds done pairwise_mean_ari={payload['pairwise_mean_ari']}")
    if ablation in {"all", "a2"}:
        rows = run_a2_min_cluster(root / "a2_min_cluster" / run_ts)
        for item in rows:
            row = _blank_row("a2_min_cluster", run_ts, "min_cluster_size", str(item["min_cluster_size"]))
            row["n_topics"] = item["n_topics"]
            row["n_noise"] = item["n_noise"]
            row["noise_share"] = item["noise_share"]
            append_summary_row(row)
        print("ablation=a2_min_cluster done")
    if ablation in {"all", "a3"}:
        payload = run_a3_minilm(root / "a3_minilm" / run_ts, production_original)
        row = _blank_row("a3_minilm", run_ts, "embedding_model", "all-MiniLM-L6-v2")
        row["n_topics"] = payload["n_topics"]
        row["n_noise"] = payload["n_noise"]
        row["noise_share"] = payload["noise_share"]
        row["spearman_q5_keep_rate"] = payload["spearman_q5_keep_rate"]
        append_summary_row(row)
        print(f"ablation=a3_minilm done spearman_q5={payload['spearman_q5_keep_rate']}")
    if ablation in {"all", "a4"}:
        a4_dir = root / "a4_design" / run_ts
        run_a4_design_comparison(production_original, mirror_run, production_joint, assign_run, a4_dir)
        for variant in ("separate", "joint", "original_assign_mirror"):
            metrics = json.loads((a4_dir / variant / "q2_q3_metrics.json").read_text(encoding="utf-8"))
            row = _blank_row("a4_design", run_ts, "fit_design", variant)
            row["q2_pair_agreement"] = metrics["q2_pair_agreement"]
            row["q3_role_dominated_topics"] = metrics["q3_role_dominated_topics"]
            append_summary_row(row)
        print("ablation=a4_design done")
    if ablation in {"all", "a5"}:
        payload = run_a5_outliers(root / "a5_outliers" / run_ts, production_original)
        row = _blank_row("a5_outliers", run_ts, "reduce_outliers", "embeddings")
        row["n_topics"] = payload["n_topics"]
        row["n_noise"] = payload["noise_on"]
        row["noise_share"] = payload["noise_share_on"]
        row["spearman_q5_keep_rate"] = payload["spearman_q5_keep_rate"]
        row["notes"] = f"noise_off={payload['noise_off']} noise_on={payload['noise_on']}"
        append_summary_row(row)
        print(
            "ablation=a5_outliers done "
            f"noise_off={payload['noise_share_off']} noise_on={payload['noise_share_on']} "
            f"spearman_q5={payload['spearman_q5_keep_rate']}"
        )
    if ablation in {"all", "review"}:
        review_dir = paths.EXPERIMENT_ROOT / "outputs" / "reviews" / run_ts
        write_review("original", production_original, _latest(paths.labels_dir("original")), review_dir, seed)
        write_review("joint", production_joint, _latest(paths.labels_dir("joint")), review_dir, seed)
        print(f"review_dir={review_dir}")
    print(f"summary_csv={root / 'summary.csv'}")


def main() -> None:
    """CLI entry for ablations and review export."""
    parser = argparse.ArgumentParser(description="Run Part 3 BERTopic ablations.")
    parser.add_argument("--ablation", choices=["all", "a0", "a1", "a2", "a3", "a4", "a5", "review"], default="all")
    parser.add_argument("--production-original-run-dir", type=Path, default=None)
    parser.add_argument("--production-joint-run-dir", type=Path, default=None)
    parser.add_argument("--q5-outcomes-csv", type=Path, default=None)
    parser.add_argument("--cross-role-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    original = args.production_original_run_dir or _latest(paths.topics_dir("original"))
    joint = args.production_joint_run_dir or _latest(paths.topics_dir("joint"))
    if not str(original).startswith(EXPERIMENT) and not original.is_absolute():
        original = Path(EXPERIMENT) / original
    run_selected(args.ablation, args.seed, original, joint)


if __name__ == "__main__":
    main()
