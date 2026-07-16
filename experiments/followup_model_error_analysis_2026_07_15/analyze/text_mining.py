"""Phase 3a: naive unigram/bigram text mining on V1 extracted features."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from experiments.followup_model_error_analysis_2026_07_15.analyze.common import (
    _append_progress,
    _now,
    load_feature_rows,
)

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = EXPERIMENT_DIR / "outputs" / "text_mining"

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "with",
    "as",
    "by",
    "from",
    "that",
    "this",
    "it",
    "its",
    "at",
    "not",
    "no",
    "vs",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(str(text).lower()) if t not in STOPWORDS and len(t) > 1]


def feature_text(row: pd.Series) -> str:
    return " ".join(
        [
            str(row.get("feature_name", "")),
            str(row.get("feature_value", "")),
            str(row.get("evidence_span", "")),
        ]
    )


def count_ngrams(texts: list[str], n: int) -> Counter:
    counts: Counter = Counter()
    for text in texts:
        toks = tokenize(text)
        if n == 1:
            counts.update(toks)
        else:
            counts.update(" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1))
    return counts


def plot_top_terms(counts: Counter, bucket: str, out_path: Path, top_n: int = 20) -> None:
    items = counts.most_common(top_n)
    if not items:
        return
    terms, vals = zip(*items)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(list(reversed(terms)), list(reversed(vals)), color="#3d5a80")
    ax.set_title(f"Top {top_n} terms — {bucket.upper()} (V1 features)")
    ax.set_xlabel("count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def log_odds_fp_vs_tn(
    fp_uni: Counter, tn_uni: Counter, top_k: int = 25
) -> pd.DataFrame:
    vocab = set(fp_uni) | set(tn_uni)
    rows = []
    fp_n = sum(fp_uni.values()) + 1e-9
    tn_n = sum(tn_uni.values()) + 1e-9
    for term in vocab:
        a = fp_uni.get(term, 0) + 0.5
        b = tn_uni.get(term, 0) + 0.5
        ratio = (a / fp_n) / (b / tn_n)
        rows.append(
            {
                "term": term,
                "fp_count": fp_uni.get(term, 0),
                "tn_count": tn_uni.get(term, 0),
                "fp_tn_ratio": ratio,
            }
        )
    out = pd.DataFrame(rows).sort_values("fp_tn_ratio", ascending=False)
    return out.head(top_k)


def run_text_mining() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_feature_rows()
    df["text"] = df.apply(feature_text, axis=1)

    _append_progress(
        f"## [{_now()}] Phase 3a — Text mining\n\n"
        f"- Status: started\n"
        f"- Scope: v1\n"
        f"- Details: feature_rows={len(df)} buckets={sorted(df['confusion_bucket'].unique())}\n"
    )

    snippet_lines = [
        f"# Text mining progress snippet (V1)",
        f"",
        f"Generated: {_now()}",
        f"Feature rows: {len(df)}",
        f"",
    ]

    unigram_by_bucket: dict[str, Counter] = {}
    for bucket, part in df.groupby("confusion_bucket"):
        texts = part["text"].tolist()
        uni = count_ngrams(texts, 1)
        bi = count_ngrams(texts, 2)
        unigram_by_bucket[str(bucket)] = uni

        uni_df = pd.DataFrame(
            [{"term": t, "count": c, "bucket": bucket} for t, c in uni.most_common()]
        )
        bi_df = pd.DataFrame(
            [{"term": t, "count": c, "bucket": bucket} for t, c in bi.most_common()]
        )
        uni_path = OUT_DIR / f"unigram_counts_{bucket}.csv"
        bi_path = OUT_DIR / f"bigram_counts_{bucket}.csv"
        uni_df.to_csv(uni_path, index=False)
        bi_df.to_csv(bi_path, index=False)
        plot_path = OUT_DIR / f"top_terms_{bucket}.png"
        plot_top_terms(uni, str(bucket), plot_path)

        top5 = ", ".join(f"{t}({c})" for t, c in uni.most_common(5))
        snippet_lines.append(f"## {str(bucket).upper()}")
        snippet_lines.append(f"- rows: {len(part)}")
        snippet_lines.append(f"- top unigrams: {top5}")
        snippet_lines.append(f"- artifacts: `{uni_path.name}`, `{bi_path.name}`, `{plot_path.name}`")
        snippet_lines.append("")

    comparison = None
    if "fp" in unigram_by_bucket and "tn" in unigram_by_bucket:
        comparison = log_odds_fp_vs_tn(unigram_by_bucket["fp"], unigram_by_bucket["tn"])
        comparison.to_csv(OUT_DIR / "fp_vs_tn_enriched_terms.csv", index=False)
        snippet_lines.append("## FP vs TN enriched terms (top ratio)")
        for _, row in comparison.head(10).iterrows():
            snippet_lines.append(
                f"- `{row['term']}`: fp={int(row['fp_count'])} tn={int(row['tn_count'])} "
                f"ratio={row['fp_tn_ratio']:.2f}"
            )
        snippet_lines.append("")

    snippet_path = OUT_DIR / "progress_snippet.md"
    snippet_path.write_text("\n".join(snippet_lines) + "\n")

    summary = {
        "scope": "v1",
        "n_feature_rows": int(len(df)),
        "buckets": sorted(df["confusion_bucket"].astype(str).unique().tolist()),
        "n_posts": int(df["post_id"].nunique()),
        "snippet": str(snippet_path.relative_to(EXPERIMENT_DIR)),
    }
    (OUT_DIR / "text_mining_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    _append_progress(
        f"## [{_now()}] Phase 3a — Text mining\n\n"
        f"- Status: completed\n"
        f"- Scope: v1\n"
        f"- Details: {json.dumps(summary)}\n"
        f"- Artifacts: `outputs/text_mining/` (see progress_snippet.md)\n"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run_text_mining()


if __name__ == "__main__":
    main()
