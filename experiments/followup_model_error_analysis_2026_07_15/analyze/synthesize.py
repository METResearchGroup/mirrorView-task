"""Phase 4: assemble RESULTS.md from V1 artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
OUT = EXPERIMENT_DIR / "outputs"
PROGRESS_PATH = EXPERIMENT_DIR / "progress.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _top_terms(bucket: str, n: int = 10) -> list[str]:
    path = OUT / "text_mining" / f"unigram_counts_{bucket}.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path).head(n)
    return [f"{r.term} ({int(r.count)})" for r in df.itertuples(index=False)]


def synthesize() -> Path:
    split = _read_json(OUT / "confusion_splits" / "split_summary.json")
    plan = _read_json(OUT / "llm_features" / "v1_batch_plan.json")
    cost = _read_json(OUT / "llm_features" / "cost_summary.json")
    cluster_cost = _read_json(OUT / "clustering" / "cost_summary.json")
    merged = _read_json(OUT / "clustering" / "clusters_merged.json")
    mining = _read_json(OUT / "text_mining" / "text_mining_summary.json")
    manifest = _read_json(OUT / "run_manifest.json")

    n_batches = len(plan.get("batches", []))
    n_posts = sum(b.get("n_posts", 0) for b in plan.get("batches", []))
    extract_cost = float(cost.get("total_cost_usd", 0) or 0)
    clustering_cost = float(cluster_cost.get("total_cost_usd", 0) or 0)
    total_cost = extract_cost + clustering_cost
    new_calls = int(cost.get("new_calls", cost.get("unique_completed_batches", 0)) or 0)
    completed = int(cost.get("unique_completed_batches", 0) or 0)

    fp_themes = merged.get("fp_specific_themes") or []
    cross = merged.get("cross_cutting_themes") or []
    clusters = merged.get("clusters") or []

    # FP vs TN terms
    fp_tn_path = OUT / "text_mining" / "fp_vs_tn_enriched_terms.csv"
    fp_enriched = []
    if fp_tn_path.exists():
        fp_enriched = [
            f"`{r.term}` (ratio={r.fp_tn_ratio:.2f})"
            for r in pd.read_csv(fp_tn_path).head(8).itertuples(index=False)
        ]

    buckets = split.get("buckets", {})
    lines = [
        "# RESULTS — Follow-up Model Error Analysis (LLM Feature Extraction)",
        "",
        f"**Experiment:** `experiments/followup_model_error_analysis_2026_07_15/`  ",
        f"**Scope:** **V1 pilot** (exactly {n_batches} extraction batches; V2 not run)  ",
        f"**Primary model:** `gpt-5.5` (fallback `gpt-5.4-nano` only if needed)  ",
        f"**Generated:** {_now()}",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "- **V1 pilot only:** We extracted high-confidence linguistic features for ≤320 Study 2 posts "
        f"across {n_batches} planned batches (FP=8, FN=4, TP=4, TN=4) — **not** the full 8,791-post corpus.",
        f"- **Confusion splits match prior labels:** TP={buckets.get('tp', {}).get('rows')}, "
        f"TN={buckets.get('tn', {}).get('rows')}, FP={buckets.get('fp', {}).get('rows')}, "
        f"FN={buckets.get('fn', {}).get('rows')} (expected 2067/3572/2406/746).",
        "- **FP (Qwen over-predicts remove) is the priority slice:** text mining and clustering "
        "highlight recurring surface/pragmatic patterns among false-positive removes vs true keeps.",
        f"- **Cost:** extraction ≈ **${extract_cost:.2f}** ({completed} completed batches); "
        f"clustering ≈ **${clustering_cost:.2f}**; pipeline ≈ **${total_cost:.2f}**. "
        "V2 (~$140 extraction) was **not** run.",
        "- **Limitation:** Findings are provisional on a ~3.6% stratified sample of posts; "
        "do not generalize as full-corpus prevalence without V2 approval.",
        "",
        "## 2. Confusion split counts",
        "",
        "| Bucket | Rows | Expected | Match |",
        "| --- | ---: | ---: | --- |",
    ]
    for b in ("tp", "tn", "fp", "fn"):
        info = buckets.get(b, {})
        lines.append(
            f"| {b.upper()} | {info.get('rows')} | {info.get('expected')} | "
            f"{'yes' if info.get('match_expected') else 'NO'} |"
        )
    lines.extend(
        [
            "",
            f"Source: `outputs/confusion_splits/split_summary.json`. "
            f"Sanity: `{json.dumps(split.get('sanity', {}))}`.",
            "",
            "## 3. V1 coverage",
            "",
            f"- Planned batches: **{n_batches}** (`outputs/llm_features/v1_batch_plan.json`)",
            f"- Allocation: FP=8, FN=4, TP=4, TN=4 (chunk size 16)",
            f"- Posts in plan: **{n_posts}** (≤320)",
            f"- Completed extraction batches (unique): **{completed}**",
            f"- New API calls this latest extraction run: **{new_calls}**",
            f"- Feature rows mined: **{mining.get('n_feature_rows', 'n/a')}** "
            f"across **{mining.get('n_posts', 'n/a')}** posts",
            "",
            "## 4. Top surface/semantic patterns per bucket (text mining)",
            "",
        ]
    )
    for b in ("fp", "fn", "tp", "tn"):
        tops = _top_terms(b, 8)
        if tops:
            lines.append(f"### {b.upper()}")
            lines.append(", ".join(tops))
            lines.append("")
    if fp_enriched:
        lines.append("### FP-enriched vs TN (ratio)")
        lines.append(", ".join(fp_enriched))
        lines.append("")
        lines.append("See `outputs/text_mining/fp_vs_tn_enriched_terms.csv` and `top_terms_*.png`.")
        lines.append("")

    lines.extend(
        [
            "## 5. LLM cluster interpretations (V1 subset)",
            "",
        ]
    )
    if not clusters:
        lines.append("_No clustering output found._")
        lines.append("")
    else:
        for c in clusters[:12]:
            lines.append(f"### [{c.get('cluster_id')}] {c.get('cluster_label')}")
            mix = c.get("bucket_mix")
            if hasattr(mix, "model_dump"):
                mix = mix.model_dump()
            lines.append(f"- bucket_mix: `{mix}`")
            defs = ", ".join((c.get("defining_features") or [])[:8])
            lines.append(f"- defining features: {defs}")
            lines.append(f"- {c.get('interpretation', '')}")
            lines.append("")
        if cross:
            lines.append("### Cross-cutting themes")
            for t in cross:
                lines.append(f"- {t}")
            lines.append("")

    lines.extend(
        [
            "## 6. FP-focused findings",
            "",
            "When Qwen predicts **remove** but humans said **keep** (FP), recurring themes include:",
            "",
        ]
    )
    if fp_themes:
        for t in fp_themes:
            lines.append(f"- {t}")
    else:
        lines.append(
            "- See cluster summary and FP text-mining ratios; FP themes were not returned "
            "as a separate list."
        )
    lines.extend(
        [
            "",
            "These are **pilot** signals on ≤128 FP posts (8 batches × 16). "
            "They suggest which linguistic cues may co-occur with over-removal, "
            "not causal explanations of Qwen.",
            "",
            "## 7. Limitations",
            "",
            f"- **20-call V1 pilot** only (~{n_posts} posts); full corpus would need ~552 extraction calls.",
            "- Confidence gate **0.85** drops medium/low features.",
            "- No Bedrock / Titan re-run; labels reused from prior experiment.",
            f"- API cost (V1): extraction ${extract_cost:.4f} + clustering ${clustering_cost:.4f} "
            f"= **${total_cost:.4f}** (`outputs/llm_features/cost_summary.json`, "
            "`outputs/clustering/cost_summary.json`).",
            "- **V2 not run** (would require explicit ~$140 / ~$145–$150 cost approval).",
            f"- Run manifest: `outputs/run_manifest.json` (v2_cost_approval="
            f"{manifest.get('v2_cost_approval', False)}).",
            "",
            "## 8. Artifact index",
            "",
            "| Artifact | Path |",
            "| --- | --- |",
            "| Spec | `spec.md` |",
            "| Progress log | `progress.md` |",
            "| Confusion splits | `outputs/confusion_splits/` |",
            "| V1 batch plan | `outputs/llm_features/v1_batch_plan.json` |",
            "| Feature CSVs | `outputs/llm_features/{tp,tn,fp,fn}/batch_*.csv` |",
            "| Extraction cost | `outputs/llm_features/cost_summary.json` |",
            "| Text mining | `outputs/text_mining/` |",
            "| Clustering | `outputs/clustering/` |",
            "| Run manifest | `outputs/run_manifest.json` |",
            "",
        ]
    )

    results_path = EXPERIMENT_DIR / "RESULTS.md"
    results_path.write_text("\n".join(lines) + "\n")

    with PROGRESS_PATH.open("a", encoding="utf-8") as f:
        f.write(
            f"## [{_now()}] Phase 4 — Synthesis\n\n"
            f"- Status: completed\n"
            f"- Scope: v1\n"
            f"- Details: Wrote RESULTS.md (extract_cost=${extract_cost:.4f}, "
            f"clustering_cost=${clustering_cost:.4f}, total=${total_cost:.4f})\n"
            f"- Artifacts: `RESULTS.md`\n\n"
        )
    print(f"Wrote {results_path}")
    return results_path


def main() -> None:
    synthesize()


if __name__ == "__main__":
    main()
