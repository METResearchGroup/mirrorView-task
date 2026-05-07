"""PRIME-label analysis on linked MirrorView run data.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/main.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.analysis.prime_classifier.link_mirrorview_run_to_labels import (
    get_mirrorview_run_data_with_labels,
)
from lib.timestamp_utils import get_current_timestamp

LABEL_ORIGINAL_COL = "prime_clf_label_original_text"
LABEL_MIRROR_COL = "prime_clf_label_mirrors"
PRIME_CLASSIFIER_DIR = Path(__file__).resolve().parent


class PrimeLabelAnalyzer:
    """Analyze PRIME classifier labels attached to MirrorView run data."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df.copy()
        self.timestamp = get_current_timestamp()
        self.output_dir = PRIME_CLASSIFIER_DIR / "outputs" / self.timestamp
        self.results: dict[str, Any] = {
            "original_text_analysis": None,
            "mirror_text_analysis": None,
            "pairwise_analysis": None,
            "keep_remove_analysis": None,
        }

    def original_text_analysis(self) -> None:
        """PRIME-label rates for original text by partyxcondition (+ marginals)."""
        self.results["original_text_analysis"] = self._partition_positive_rate(LABEL_ORIGINAL_COL)

    def mirror_text_analysis(self) -> None:
        """PRIME-label rates for mirrored text by partyxcondition (+ marginals)."""
        self.results["mirror_text_analysis"] = self._partition_positive_rate(LABEL_MIRROR_COL)

    def pairwise_analysis(self) -> None:
        """Pairwise agreement/shift between original and mirrored PRIME labels."""
        d = self.df.copy()
        d = d.dropna(subset=[LABEL_ORIGINAL_COL, LABEL_MIRROR_COL])
        if d.empty:
            self.results["pairwise_analysis"] = pd.DataFrame()
            return

        d[LABEL_ORIGINAL_COL] = d[LABEL_ORIGINAL_COL].astype(bool)
        d[LABEL_MIRROR_COL] = d[LABEL_MIRROR_COL].astype(bool)
        d["label_match"] = d[LABEL_ORIGINAL_COL] == d[LABEL_MIRROR_COL]
        d["became_more_positive"] = (~d[LABEL_ORIGINAL_COL]) & d[LABEL_MIRROR_COL]
        d["became_less_positive"] = d[LABEL_ORIGINAL_COL] & (~d[LABEL_MIRROR_COL])

        summary = (
            d.groupby(["party_group", "condition"], dropna=False)
            .agg(
                n=("post_id", "count"),
                match_rate=("label_match", "mean"),
                more_positive_rate=("became_more_positive", "mean"),
                less_positive_rate=("became_less_positive", "mean"),
            )
            .reset_index()
        )
        self.results["pairwise_analysis"] = summary

    def keep_remove_analysis(self) -> None:
        """PRIME-label rates split by keep/remove decision and key partitions."""
        if "decision" not in self.df.columns:
            self.results["keep_remove_analysis"] = pd.DataFrame()
            return

        d = self.df[self.df["decision"].astype(str).str.lower().isin(["keep", "remove"])].copy()
        if d.empty:
            self.results["keep_remove_analysis"] = pd.DataFrame()
            return

        d = d.dropna(subset=[LABEL_ORIGINAL_COL, LABEL_MIRROR_COL])
        if d.empty:
            self.results["keep_remove_analysis"] = pd.DataFrame()
            return
        d[LABEL_ORIGINAL_COL] = d[LABEL_ORIGINAL_COL].astype(bool)
        d[LABEL_MIRROR_COL] = d[LABEL_MIRROR_COL].astype(bool)

        summary = (
            d.groupby(["party_group", "condition", "phase", "decision"], dropna=False)
            .agg(
                n=("post_id", "count"),
                original_positive_rate=(LABEL_ORIGINAL_COL, "mean"),
                mirror_positive_rate=(LABEL_MIRROR_COL, "mean"),
            )
            .reset_index()
        )
        self.results["keep_remove_analysis"] = summary

    def show_results(self) -> None:
        """Print analysis outputs."""
        print("\n=== Original text PRIME label rates ===")
        print(self.results["original_text_analysis"])

        print("\n=== Mirror text PRIME label rates ===")
        print(self.results["mirror_text_analysis"])

        print("\n=== Pairwise label change analysis ===")
        print(self.results["pairwise_analysis"])

        print("\n=== Keep/remove label analysis ===")
        print(self.results["keep_remove_analysis"])

    def visualize_results(self) -> None:
        """Render matplotlib charts from current analysis outputs."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        original = self.results["original_text_analysis"]
        mirror = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if isinstance(original, dict) and isinstance(mirror, dict):
            overall = pd.DataFrame(
                [
                    {"series": "original", "positive_rate": original.get("all", float("nan"))},
                    {"series": "mirror", "positive_rate": mirror.get("all", float("nan"))},
                ]
            )
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.bar(overall["series"], overall["positive_rate"], color=["#4C78A8", "#F58518"])
            ax.set_ylim(0.0, 1.0)
            ax.set_ylabel("PRIME rate")
            ax.set_title("Overall PRIME rate")
            fig.tight_layout()
            fig.savefig(self.output_dir / "overall_positive_rate.png", dpi=200)
            plt.close(fig)

        if isinstance(pairwise, pd.DataFrame) and not pairwise.empty:
            pairwise_plot = pairwise.copy()
            pairwise_plot["group"] = (
                pairwise_plot["party_group"].astype(str) + "_" + pairwise_plot["condition"].astype(str)
            )
            fig, ax = plt.subplots(figsize=(10, 5))
            x = range(len(pairwise_plot))
            ax.bar(x, pairwise_plot["more_positive_rate"], label="more_positive_rate", color="#54A24B")
            ax.bar(
                x,
                pairwise_plot["less_positive_rate"],
                bottom=pairwise_plot["more_positive_rate"],
                label="less_positive_rate",
                color="#E45756",
            )
            ax.plot(x, pairwise_plot["match_rate"], marker="o", color="#4C78A8", label="match_rate")
            ax.set_xticks(list(x))
            ax.set_xticklabels(pairwise_plot["group"], rotation=30, ha="right")
            ax.set_ylim(0.0, 1.0)
            ax.set_ylabel("Rate")
            ax.set_title("Pairwise label shift and match rates")
            ax.legend()
            fig.tight_layout()
            fig.savefig(self.output_dir / "pairwise_shift_rates.png", dpi=200)
            plt.close(fig)

        if isinstance(keep_remove, pd.DataFrame) and not keep_remove.empty:
            decision_summary = (
                keep_remove.groupby("decision", dropna=False)[
                    ["original_positive_rate", "mirror_positive_rate"]
                ]
                .mean()
                .reset_index()
            )
            fig, ax = plt.subplots(figsize=(7, 4))
            x = range(len(decision_summary))
            width = 0.35
            ax.bar(
                [i - width / 2 for i in x],
                decision_summary["original_positive_rate"],
                width=width,
                label="original_positive_rate",
                color="#4C78A8",
            )
            ax.bar(
                [i + width / 2 for i in x],
                decision_summary["mirror_positive_rate"],
                width=width,
                label="mirror_positive_rate",
                color="#F58518",
            )
            ax.set_xticks(list(x))
            ax.set_xticklabels(decision_summary["decision"].astype(str))
            ax.set_ylim(0.0, 1.0)
            ax.set_ylabel("PRIME rate")
            ax.set_title("Keep vs remove PRIME rates")
            ax.legend()
            fig.tight_layout()
            fig.savefig(self.output_dir / "keep_remove_positive_rates.png", dpi=200)
            plt.close(fig)

    def save_results(self) -> None:
        """Persist analysis outputs as CSV files in the timestamped output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        original = self.results["original_text_analysis"]
        mirror = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if isinstance(original, dict):
            pd.DataFrame(
                [{"partition": key, "positive_rate": value} for key, value in original.items()]
            ).to_csv(self.output_dir / "analysis_original_text.csv", index=False)

        if isinstance(mirror, dict):
            pd.DataFrame(
                [{"partition": key, "positive_rate": value} for key, value in mirror.items()]
            ).to_csv(self.output_dir / "analysis_mirrors.csv", index=False)

        if isinstance(pairwise, pd.DataFrame):
            pairwise.to_csv(self.output_dir / "analysis_pairwise.csv", index=False)

        if isinstance(keep_remove, pd.DataFrame):
            keep_remove.to_csv(self.output_dir / "analysis_keep_remove.csv", index=False)

    def _partition_positive_rate(self, label_col: str) -> dict[str, float]:
        d = self.df.copy()
        d = d.dropna(subset=[label_col, "party_group", "condition"])
        if d.empty:
            return {"all": float("nan")}

        d[label_col] = d[label_col].astype(bool)
        out: dict[str, float] = {}

        for (party, condition), grp in d.groupby(["party_group", "condition"], sort=True):
            out[f"{party}_{condition}"] = float(grp[label_col].mean())
        for party, grp in d.groupby("party_group", sort=True):
            out[f"{party}_all"] = float(grp[label_col].mean())
        for condition, grp in d.groupby("condition", sort=True):
            out[f"all_{condition}"] = float(grp[label_col].mean())

        out["all"] = float(d[label_col].mean())
        return out


def main() -> None:
    df = get_mirrorview_run_data_with_labels()

    analyzer = PrimeLabelAnalyzer(df)
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()
    analyzer.show_results()
    analyzer.visualize_results()
    analyzer.save_results()


if __name__ == "__main__":
    main()
