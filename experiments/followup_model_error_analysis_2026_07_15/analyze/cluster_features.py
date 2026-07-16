"""Phase 3b: LLM clustering on V1 feature subset only."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

from experiments.followup_model_error_analysis_2026_07_15.extract.client import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    get_llm,
)
from experiments.followup_model_error_analysis_2026_07_15.extract.pricing import (
    estimate_call_cost_usd,
    usage_from_langchain_message,
)
from experiments.followup_model_error_analysis_2026_07_15.extract.prompts import (
    CLUSTER_MERGE_PROMPT,
    CLUSTERING_PROMPT,
)
from experiments.followup_model_error_analysis_2026_07_15.analyze.common import (
    _append_progress,
    _now,
    load_feature_rows,
)
from experiments.followup_model_error_analysis_2026_07_15.extract.schemas import (
    ClusteringResult,
)

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = EXPERIMENT_DIR / "outputs" / "clustering"

# ~4 chars/token; stay under ~100k tokens input
MAX_CHARS_PER_SHARD = 100_000 * 4

_CLUSTER_PROMPT = ChatPromptTemplate.from_messages([("human", CLUSTERING_PROMPT)])
_MERGE_PROMPT = ChatPromptTemplate.from_messages([("human", CLUSTER_MERGE_PROMPT)])


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def build_corpus(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (post_id, bucket), part in df.groupby(["post_id", "confusion_bucket"]):
        feats = []
        seen = set()
        for r in part.itertuples(index=False):
            key = (r.category, r.feature_name, r.feature_value)
            if key in seen:
                continue
            seen.add(key)
            feats.append(
                {
                    "category": r.category,
                    "feature_name": r.feature_name,
                    "feature_value": r.feature_value,
                    "confidence": float(r.confidence),
                    "evidence_span": str(r.evidence_span)[:160],
                }
            )
        rows.append(
            {
                "post_id": str(post_id),
                "confusion_bucket": str(bucket),
                "features": feats,
            }
        )
    return pd.DataFrame(rows)


def to_jsonl_lines(corpus: pd.DataFrame) -> list[str]:
    lines = []
    for row in corpus.itertuples(index=False):
        compact = {
            "post_id": row.post_id,
            "bucket": row.confusion_bucket,
            "features": [
                f"{f['category']}:{f['feature_name']}={f['feature_value']}"
                for f in row.features
            ],
        }
        lines.append(json.dumps(compact, ensure_ascii=False))
    return lines


def shard_lines(lines: list[str], max_chars: int = MAX_CHARS_PER_SHARD) -> list[list[str]]:
    shards: list[list[str]] = []
    current: list[str] = []
    size = 0
    for line in lines:
        add = len(line) + 1
        if current and size + add > max_chars:
            shards.append(current)
            current = []
            size = 0
        current.append(line)
        size += add
    if current:
        shards.append(current)
    return shards


def invoke_clustering(corpus_jsonl: str, shard_id: str, model: str) -> tuple[ClusteringResult, dict, str]:
    llm = get_llm(model)
    structured = llm.with_structured_output(
        ClusteringResult, include_raw=True, method="function_calling"
    )
    chain = _CLUSTER_PROMPT | structured
    result = chain.invoke({"corpus_jsonl": corpus_jsonl})
    if isinstance(result, dict) and "parsed" in result:
        parsed = result["parsed"]
        usage = usage_from_langchain_message(result.get("raw"))
    else:
        parsed = result
        usage = {}
    if parsed is None:
        raise RuntimeError(f"Clustering parse failed for {shard_id}")
    parsed.shard_id = shard_id  # type: ignore[misc]
    return parsed, usage, model


def invoke_merge(shard_results: list[dict], model: str) -> tuple[ClusteringResult, dict, str]:
    llm = get_llm(model)
    structured = llm.with_structured_output(
        ClusteringResult, include_raw=True, method="function_calling"
    )
    chain = _MERGE_PROMPT | structured
    result = chain.invoke(
        {"shard_results_json": json.dumps(shard_results, ensure_ascii=False, indent=2)}
    )
    if isinstance(result, dict) and "parsed" in result:
        parsed = result["parsed"]
        usage = usage_from_langchain_message(result.get("raw"))
    else:
        parsed = result
        usage = {}
    if parsed is None:
        raise RuntimeError("Merge parse failed")
    parsed.shard_id = "merged"  # type: ignore[misc]
    return parsed, usage, model


def run_clustering(*, max_shards: int = 2) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_feature_rows()
    corpus = build_corpus(df)
    corpus_path = OUT_DIR / "feature_corpus.parquet"
    # Flatten for parquet storage
    flat_rows = []
    for row in corpus.itertuples(index=False):
        for f in row.features:
            flat_rows.append(
                {
                    "post_id": row.post_id,
                    "confusion_bucket": row.confusion_bucket,
                    "category": f["category"],
                    "feature_name": f["feature_name"],
                    "feature_value": f["feature_value"],
                    "confidence": f["confidence"],
                    "evidence_span": f["evidence_span"],
                }
            )
    pd.DataFrame(flat_rows).to_parquet(corpus_path, index=False)

    lines = to_jsonl_lines(corpus)
    shards = shard_lines(lines)[:max_shards]

    _append_progress(
        f"## [{_now()}] Phase 3b — Clustering\n\n"
        f"- Status: started\n"
        f"- Scope: v1\n"
        f"- Details: posts={len(corpus)} feature_rows={len(df)} shards={len(shards)} "
        f"(V1 subset only; max_shards={max_shards})\n"
    )

    cost_log: list[dict] = []
    shard_results: list[dict] = []

    for i, shard in enumerate(tqdm(shards, desc="Clustering shards", unit="call", leave=True)):
        shard_id = f"shard_{i:02d}"
        out_path = OUT_DIR / f"cluster_batch_{i}.json"
        if out_path.exists():
            data = json.loads(out_path.read_text())
            shard_results.append(data)
            tqdm.write(f"skip existing {out_path.name}")
            continue

        corpus_jsonl = "\n".join(shard)
        model_used = PRIMARY_MODEL
        try:
            parsed, usage, model_used = invoke_clustering(corpus_jsonl, shard_id, PRIMARY_MODEL)
        except Exception:  # noqa: BLE001
            parsed, usage, model_used = invoke_clustering(corpus_jsonl, shard_id, FALLBACK_MODEL)

        payload = parsed.model_dump()
        _atomic_write_text(out_path, json.dumps(payload, indent=2) + "\n")
        shard_results.append(payload)
        cost = estimate_call_cost_usd(model_used, usage)
        cost_log.append(
            {
                "phase": "clustering",
                "shard_id": shard_id,
                "model": model_used,
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "cached_tokens": int(usage.get("cached_tokens", 0)),
                "cost_usd": round(cost, 6),
                "call_timestamp": _now(),
                "scope": "v1",
            }
        )

    merged_path = OUT_DIR / "clusters_merged.json"
    if len(shard_results) > 1 and not merged_path.exists():
        model_used = PRIMARY_MODEL
        try:
            parsed, usage, model_used = invoke_merge(shard_results, PRIMARY_MODEL)
        except Exception:  # noqa: BLE001
            parsed, usage, model_used = invoke_merge(shard_results, FALLBACK_MODEL)
        payload = parsed.model_dump()
        _atomic_write_text(merged_path, json.dumps(payload, indent=2) + "\n")
        cost = estimate_call_cost_usd(model_used, usage)
        cost_log.append(
            {
                "phase": "clustering_merge",
                "shard_id": "merged",
                "model": model_used,
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "cached_tokens": int(usage.get("cached_tokens", 0)),
                "cost_usd": round(cost, 6),
                "call_timestamp": _now(),
                "scope": "v1",
            }
        )
    elif len(shard_results) == 1:
        single_result = shard_results[0].copy()
        single_result["shard_id"] = "merged"
        _atomic_write_text(merged_path, json.dumps(single_result, indent=2) + "\n")

    # Prefer existing cost log merge without double-count
    existing_path = OUT_DIR / "cost_log.json"
    existing = json.loads(existing_path.read_text()) if existing_path.exists() else []
    seen = {r.get("shard_id") for r in existing}
    for r in cost_log:
        if r["shard_id"] not in seen:
            existing.append(r)
            seen.add(r["shard_id"])
    _atomic_write_text(existing_path, json.dumps(existing, indent=2) + "\n")

    total_cost = sum(float(r.get("cost_usd", 0)) for r in existing)
    cost_summary = {
        "scope": "v1",
        "model_primary": PRIMARY_MODEL,
        "model_fallback": FALLBACK_MODEL,
        "n_shards": len(shards),
        "new_calls_this_run": len(cost_log),
        "total_cost_usd": round(total_cost, 6),
        "calls": existing,
        "updated_at": _now(),
    }
    _atomic_write_text(
        OUT_DIR / "cost_summary.json", json.dumps(cost_summary, indent=2) + "\n"
    )

    merged = json.loads(merged_path.read_text()) if merged_path.exists() else {}
    summary_md = [
        "# Cluster summary (V1 pilot)",
        "",
        f"Generated: {_now()}",
        f"Posts in corpus: {len(corpus)}",
        f"Feature rows: {len(df)}",
        f"Shards: {len(shards)}",
        f"Clustering cost USD: {total_cost:.4f}",
        "",
        "## FP-specific themes",
    ]
    for t in merged.get("fp_specific_themes", []) or []:
        summary_md.append(f"- {t}")
    summary_md.append("")
    summary_md.append("## Cross-cutting themes")
    for t in merged.get("cross_cutting_themes", []) or []:
        summary_md.append(f"- {t}")
    summary_md.append("")
    summary_md.append("## Clusters")
    for c in merged.get("clusters", []) or []:
        summary_md.append(
            f"### [{c.get('cluster_id')}] {c.get('cluster_label')}"
        )
        summary_md.append(f"- bucket_mix: `{c.get('bucket_mix')}`")
        summary_md.append(
            f"- defining: {', '.join(c.get('defining_features', [])[:8])}"
        )
        summary_md.append(f"- {c.get('interpretation', '')}")
        summary_md.append("")

    summary_path = OUT_DIR / "cluster_summary.md"
    summary_path.write_text("\n".join(summary_md) + "\n")

    # Update root run_manifest with clustering costs
    manifest_path = EXPERIMENT_DIR / "outputs" / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        manifest["clustering_cost_summary"] = cost_summary
        manifest["updated_at"] = _now()
        _atomic_write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")

    _append_progress(
        f"## [{_now()}] Phase 3b — Clustering\n\n"
        f"- Status: completed\n"
        f"- Scope: v1\n"
        f"- Details: shards={len(shards)} new_calls={len(cost_log)} "
        f"total_cost_usd={total_cost:.4f}\n"
        f"- Artifacts: `outputs/clustering/cluster_summary.md`, "
        f"`outputs/clustering/clusters_merged.json`\n"
        f"- Cost (if LLM phase): cumulative_usd={total_cost:.4f} "
        f"new_calls={len(cost_log)} skipped={len(shards)-len(cost_log)} planned={len(shards)}\n"
    )
    print(json.dumps(cost_summary, indent=2))
    return cost_summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--max-shards", type=int, default=2, help="Cap clustering shards (V1)")
    args = p.parse_args()
    run_clustering(max_shards=args.max_shards)


if __name__ == "__main__":
    main()
