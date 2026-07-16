"""Phase 2: V1-safe LLM feature extraction (default max 20 calls).

HARD CONSTRAINTS:
- Default scope=v1, --max-calls 20
- Refuse --scope v2 / --full without --i-approve-v2-cost
- Skip existing batch CSVs; do not double-count cost
- One CSV per LLM call; unified multi-category extraction
"""

from __future__ import annotations

import argparse
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    PRICING_AS_OF,
    estimate_budget_usd,
    estimate_call_cost_usd,
    usage_from_langchain_message,
)
from experiments.followup_model_error_analysis_2026_07_15.extract.prompts import (
    UNIFIED_EXTRACTION_PROMPT,
)
from experiments.followup_model_error_analysis_2026_07_15.extract.schemas import (
    CONFIDENCE_THRESHOLD,
    BatchFeatureExtraction,
    keep_feature,
)

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
SPLITS_DIR = EXPERIMENT_DIR / "outputs" / "confusion_splits"
FEATURES_DIR = EXPERIMENT_DIR / "outputs" / "llm_features"
PROGRESS_PATH = EXPERIMENT_DIR / "progress.md"

CHUNK_SIZE = 16
V1_PLAN = {"fp": 8, "fn": 4, "tp": 4, "tn": 4}
BUCKET_FILES = {
    "tp": "true_positives.csv",
    "tn": "true_negatives.csv",
    "fp": "false_positives.csv",
    "fn": "false_negatives.csv",
}

_PROMPT = ChatPromptTemplate.from_messages([("human", UNIFIED_EXTRACTION_PROMPT)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_progress(text: str) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS_PATH.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n\n")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp_path = Path(tmp.name)
        df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def load_bucket_df(bucket: str) -> pd.DataFrame:
    path = SPLITS_DIR / BUCKET_FILES[bucket]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}; run split/split_confusion.py first."
        )
    df = pd.read_csv(path)
    return df.sort_values("post_id").reset_index(drop=True)


def chunk_rows(df: pd.DataFrame, chunk_size: int = CHUNK_SIZE) -> list[pd.DataFrame]:
    return [df.iloc[i : i + chunk_size].copy() for i in range(0, len(df), chunk_size)]


def build_v1_batch_plan() -> list[dict]:
    plan: list[dict] = []
    seen_posts: set[str] = set()
    for bucket, n_batches in V1_PLAN.items():
        df = load_bucket_df(bucket)
        chunks = chunk_rows(df)
        for chunk_idx in range(n_batches):
            if chunk_idx >= len(chunks):
                break
            chunk = chunks[chunk_idx]
            post_ids: list[str] = []
            for pid in chunk["post_id"].astype(str).tolist():
                if pid in seen_posts:
                    continue
                seen_posts.add(pid)
                post_ids.append(pid)
            batch_id = f"{bucket}/batch_{chunk_idx:04d}"
            plan.append(
                {
                    "batch_id": batch_id,
                    "bucket": bucket,
                    "chunk_idx": chunk_idx,
                    "post_ids": post_ids,
                    "n_posts": len(post_ids),
                }
            )
    return plan


def persist_v1_plan(plan: list[dict]) -> Path:
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FEATURES_DIR / "v1_batch_plan.json"
    payload = {
        "scope": "v1",
        "chunk_size": CHUNK_SIZE,
        "allocation": V1_PLAN,
        "planned_calls": len(plan),
        "batches": plan,
        "created_at": _now(),
    }
    _atomic_write_text(path, json.dumps(payload, indent=2) + "\n")
    return path


def batch_csv_path(bucket: str, chunk_idx: int) -> Path:
    return FEATURES_DIR / bucket / f"batch_{chunk_idx:04d}.csv"


def batch_meta_path(bucket: str, chunk_idx: int) -> Path:
    return FEATURES_DIR / bucket / f"batch_{chunk_idx:04d}.meta.json"


def load_cost_log() -> list[dict]:
    path = FEATURES_DIR / "cost_log.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return data.get("calls", [])


def save_cost_log(records: list[dict]) -> None:
    # Deduplicate by batch_id keeping first occurrence
    seen: set[str] = set()
    unique: list[dict] = []
    for r in records:
        bid = r.get("batch_id")
        if bid in seen:
            continue
        seen.add(bid)
        unique.append(r)
    _atomic_write_text(
        FEATURES_DIR / "cost_log.json", json.dumps(unique, indent=2) + "\n"
    )


def rebuild_cost_summary(
    *,
    scope: str,
    planned_calls: int,
    skipped_existing: int,
    new_calls: int,
) -> dict:
    records = load_cost_log()
    # Prefer meta files as source of truth for unique batch costs
    by_batch: dict[str, dict] = {}
    for bucket in V1_PLAN:
        bucket_dir = FEATURES_DIR / bucket
        if not bucket_dir.exists():
            continue
        for meta_path in sorted(bucket_dir.glob("batch_*.meta.json")):
            meta = json.loads(meta_path.read_text())
            by_batch[meta["batch_id"]] = meta
    for r in records:
        by_batch.setdefault(r["batch_id"], r)

    total_prompt = 0
    total_completion = 0
    total_cached = 0
    total_cost = 0.0
    by_bucket: dict[str, dict] = {b: {"calls": 0, "cost_usd": 0.0} for b in V1_PLAN}
    by_model: dict[str, dict] = {}

    for bid, meta in by_batch.items():
        cost = float(meta.get("cost_usd", 0.0))
        prompt = int(meta.get("prompt_tokens", 0))
        completion = int(meta.get("completion_tokens", 0))
        cached = int(meta.get("cached_tokens", 0))
        model = meta.get("model", PRIMARY_MODEL)
        bucket = meta.get("bucket") or bid.split("/")[0]
        total_prompt += prompt
        total_completion += completion
        total_cached += cached
        total_cost += cost
        by_bucket.setdefault(bucket, {"calls": 0, "cost_usd": 0.0})
        by_bucket[bucket]["calls"] += 1
        by_bucket[bucket]["cost_usd"] += cost
        by_model.setdefault(model, {"calls": 0, "cost_usd": 0.0})
        by_model[model]["calls"] += 1
        by_model[model]["cost_usd"] += cost

    summary = {
        "scope": scope,
        "model_primary": PRIMARY_MODEL,
        "model_fallback": FALLBACK_MODEL,
        "pricing_as_of": PRICING_AS_OF,
        "planned_calls": planned_calls,
        "skipped_existing": skipped_existing,
        "new_calls": new_calls,
        "unique_completed_batches": len(by_batch),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_cached_tokens": total_cached,
        "total_cost_usd": round(total_cost, 6),
        "by_bucket": by_bucket,
        "by_model": by_model,
        "updated_at": _now(),
    }
    _atomic_write_text(
        FEATURES_DIR / "cost_summary.json", json.dumps(summary, indent=2) + "\n"
    )
    return summary


def _posts_payload(chunk: pd.DataFrame, bucket: str) -> list[dict]:
    rows = []
    for row in chunk.itertuples(index=False):
        rows.append(
            {
                "post_id": str(row.post_id),
                "original_text": str(row.original_text),
                "mirrored_text": str(row.mirrored_text),
                "human_is_remove": int(row.human_is_remove),
                "qwen_is_remove": int(row.qwen_is_remove),
                "confusion_bucket": bucket,
            }
        )
    return rows


def _invoke_extraction(
    *,
    bucket: str,
    chunk_idx: int,
    posts: list[dict],
    model: str,
) -> tuple[BatchFeatureExtraction, dict, str]:
    llm = get_llm(model)
    structured = llm.with_structured_output(BatchFeatureExtraction, include_raw=True)
    chain = _PROMPT | structured
    result = chain.invoke(
        {
            "bucket": bucket,
            "chunk_idx": chunk_idx,
            "posts_json": json.dumps(posts, ensure_ascii=False, indent=2),
        }
    )
    if isinstance(result, dict) and "parsed" in result:
        parsed = result["parsed"]
        raw = result.get("raw")
        usage = usage_from_langchain_message(raw) if raw is not None else {}
    else:
        parsed = result
        usage = {}
    if parsed is None:
        raise RuntimeError(f"Structured parse failed for {bucket}/batch_{chunk_idx:04d}")
    # Ensure bucket/chunk match request
    parsed.bucket = bucket  # type: ignore[misc]
    parsed.chunk_idx = chunk_idx  # type: ignore[misc]
    return parsed, usage, model


def extract_one_batch(
    *,
    bucket: str,
    chunk_idx: int,
    post_ids: list[str],
    scope: str,
) -> dict:
    df = load_bucket_df(bucket)
    chunk = df[df["post_id"].astype(str).isin(post_ids)].copy()
    # Preserve plan order
    order = {pid: i for i, pid in enumerate(post_ids)}
    chunk["_ord"] = chunk["post_id"].astype(str).map(order)
    chunk = chunk.sort_values("_ord").drop(columns=["_ord"])
    posts = _posts_payload(chunk, bucket)

    model_used = PRIMARY_MODEL
    try:
        parsed, usage, model_used = _invoke_extraction(
            bucket=bucket, chunk_idx=chunk_idx, posts=posts, model=PRIMARY_MODEL
        )
    except Exception as primary_err:  # noqa: BLE001
        try:
            parsed, usage, model_used = _invoke_extraction(
                bucket=bucket, chunk_idx=chunk_idx, posts=posts, model=FALLBACK_MODEL
            )
        except Exception as fallback_err:  # noqa: BLE001
            raise RuntimeError(
                f"Primary ({PRIMARY_MODEL}) failed: {primary_err}; "
                f"fallback ({FALLBACK_MODEL}) failed: {fallback_err}"
            ) from fallback_err

    batch_id = f"{bucket}/batch_{chunk_idx:04d}"
    ts = _now()
    rows: list[dict] = []
    for post in parsed.posts:
        for feat in post.features:
            if not keep_feature(feat):
                continue
            rows.append(
                {
                    "post_id": post.post_id,
                    "confusion_bucket": bucket,
                    "category": feat.category.value
                    if hasattr(feat.category, "value")
                    else str(feat.category),
                    "feature_name": feat.feature_name,
                    "feature_value": feat.feature_value,
                    "is_open_ended": bool(feat.is_open_ended),
                    "confidence": float(feat.confidence),
                    "evidence_span": feat.evidence_span,
                    "rationale": feat.rationale,
                    "llm_model": model_used,
                    "chunk_idx": chunk_idx,
                    "batch_id": batch_id,
                    "call_timestamp": ts,
                }
            )

    csv_path = batch_csv_path(bucket, chunk_idx)
    out_df = pd.DataFrame(
        rows,
        columns=[
            "post_id",
            "confusion_bucket",
            "category",
            "feature_name",
            "feature_value",
            "is_open_ended",
            "confidence",
            "evidence_span",
            "rationale",
            "llm_model",
            "chunk_idx",
            "batch_id",
            "call_timestamp",
        ],
    )
    _atomic_write_csv(csv_path, out_df)

    cost = estimate_call_cost_usd(model_used, usage)
    meta = {
        "phase": "extraction",
        "batch_id": batch_id,
        "bucket": bucket,
        "chunk_idx": chunk_idx,
        "model": model_used,
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "cached_tokens": int(usage.get("cached_tokens", 0)),
        "cost_usd": round(cost, 6),
        "call_timestamp": ts,
        "scope": scope,
        "n_posts": len(posts),
        "n_features_kept": len(rows),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "csv_path": str(csv_path.relative_to(EXPERIMENT_DIR)),
    }
    _atomic_write_text(batch_meta_path(bucket, chunk_idx), json.dumps(meta, indent=2) + "\n")
    return meta


def process_bucket(
    bucket: str,
    planned: list[dict],
    *,
    max_new_calls: int,
    scope: str,
    dry_run: bool,
) -> tuple[int, int, list[dict]]:
    """Process planned batches for one bucket. Returns (skipped, new, metas)."""
    skipped = 0
    new = 0
    metas: list[dict] = []
    remaining_budget = max_new_calls

    bar = tqdm(
        planned,
        desc=f"{bucket.upper()} extraction",
        unit="call",
        leave=True,
    )
    for item in bar:
        chunk_idx = item["chunk_idx"]
        csv_path = batch_csv_path(bucket, chunk_idx)
        if csv_path.exists() and csv_path.stat().st_size > 0:
            skipped += 1
            bar.set_description(
                f"{bucket.upper()}: {new} new / {skipped} skipped / {len(planned)} planned"
            )
            continue
        if remaining_budget <= 0:
            bar.set_description(
                f"{bucket.upper()}: {new} new / {skipped} skipped / {len(planned)} planned (cap)"
            )
            continue
        if dry_run:
            new += 1
            remaining_budget -= 1
            bar.set_description(
                f"{bucket.upper()} dry-run: would call {item['batch_id']}"
            )
            continue

        meta = extract_one_batch(
            bucket=bucket,
            chunk_idx=chunk_idx,
            post_ids=item["post_ids"],
            scope=scope,
        )
        metas.append(meta)
        new += 1
        remaining_budget -= 1
        cum = sum(m["cost_usd"] for m in metas)
        bar.set_postfix(cost=f"${meta['cost_usd']:.3f}", cum=f"${cum:.3f}", new=new)
        bar.set_description(
            f"{bucket.upper()}: {new} new / {skipped} skipped / {len(planned)} planned"
        )

    return skipped, new, metas


def run_extraction(
    *,
    scope: str = "v1",
    max_calls: int = 20,
    dry_run: bool = False,
    approve_v2: bool = False,
    parallel_buckets: bool = True,
) -> dict:
    if scope == "v2" or scope == "full":
        if not approve_v2:
            raise SystemExit(
                "Refusing V2/full extraction (~552 calls, est. ~$140 on gpt-5.5). "
                "Pass --i-approve-v2-cost only after explicit user cost approval."
            )
        raise SystemExit(
            "V2 full extraction is implemented as gated but intentionally not "
            "wired for automatic full-corpus expansion in this V1 deliverable. "
            "Re-run after extending the plan loader if V2 is approved."
        )

    plan = build_v1_batch_plan()
    plan_path = persist_v1_plan(plan)
    planned_calls = len(plan)
    already_done = sum(
        1
        for item in plan
        if batch_csv_path(item["bucket"], item["chunk_idx"]).exists()
        and batch_csv_path(item["bucket"], item["chunk_idx"]).stat().st_size > 0
    )
    remaining = planned_calls - already_done
    est = estimate_budget_usd(min(max_calls, remaining), PRIMARY_MODEL)

    banner = (
        f"V1 plan: {planned_calls} batches | already done: {already_done} | "
        f"remaining API calls: {remaining} (cap max_calls={max_calls}) | "
        f"est. incremental cost ~${est:.2f} on {PRIMARY_MODEL}"
    )
    print(banner)
    _append_progress(
        f"## [{_now()}] Phase 2 — LLM feature extraction\n\n"
        f"- Status: {'dry-run' if dry_run else 'started'}\n"
        f"- Scope: v1\n"
        f"- Details: {banner}\n"
        f"- Artifacts: `{plan_path.relative_to(EXPERIMENT_DIR)}`\n"
        f"- Cost: estimate_incremental_usd={est:.2f} planned={planned_calls} "
        f"already_done={already_done}"
    )

    if dry_run:
        print(json.dumps({"plan_path": str(plan_path), "batches": plan}, indent=2)[:2000])
        return {"dry_run": True, "planned_calls": planned_calls, "estimate_usd": est}

    by_bucket: dict[str, list[dict]] = {b: [] for b in V1_PLAN}
    for item in plan:
        by_bucket[item["bucket"]].append(item)

    # Allocate max_calls across buckets in plan order (fp first)
    # Parallel workers share a simple per-bucket budget based on remaining slots.
    remaining_slots = max_calls
    bucket_budgets: dict[str, int] = {}
    for bucket in V1_PLAN:
        need = sum(
            1
            for item in by_bucket[bucket]
            if not (
                batch_csv_path(item["bucket"], item["chunk_idx"]).exists()
                and batch_csv_path(item["bucket"], item["chunk_idx"]).stat().st_size > 0
            )
        )
        allot = min(need, remaining_slots)
        bucket_budgets[bucket] = allot
        remaining_slots -= allot

    all_metas: list[dict] = []
    total_skipped = 0
    total_new = 0

    def _run(bucket: str) -> tuple[str, int, int, list[dict]]:
        sk, nw, metas = process_bucket(
            bucket,
            by_bucket[bucket],
            max_new_calls=bucket_budgets[bucket],
            scope=scope,
            dry_run=False,
        )
        return bucket, sk, nw, metas

    if parallel_buckets:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(_run, b): b
                for b in V1_PLAN
                if by_bucket[b] and bucket_budgets[b] >= 0
            }
            for fut in as_completed(futures):
                bucket, sk, nw, metas = fut.result()
                total_skipped += sk
                total_new += nw
                all_metas.extend(metas)
                cost_sum = sum(m["cost_usd"] for m in metas)
                _append_progress(
                    f"## [{_now()}] Phase 2 — {bucket.upper()} complete\n\n"
                    f"- Status: completed\n"
                    f"- Scope: v1\n"
                    f"- Details: {bucket.upper()}: planned={len(by_bucket[bucket])} "
                    f"skipped={sk} new={nw} cum_cost=${cost_sum:.4f}\n"
                    f"- Cost (if LLM phase): cumulative_usd={cost_sum:.4f} "
                    f"new_calls={nw} skipped={sk} planned={len(by_bucket[bucket])}"
                )
    else:
        for bucket in V1_PLAN:
            bucket, sk, nw, metas = _run(bucket)
            total_skipped += sk
            total_new += nw
            all_metas.extend(metas)

    # Append cost log (unique batch_ids only)
    existing = load_cost_log()
    existing_ids = {r["batch_id"] for r in existing}
    for meta in all_metas:
        if meta["batch_id"] not in existing_ids:
            existing.append(meta)
            existing_ids.add(meta["batch_id"])
    save_cost_log(existing)

    summary = rebuild_cost_summary(
        scope="v1",
        planned_calls=planned_calls,
        skipped_existing=total_skipped,
        new_calls=total_new,
    )

    manifest = {
        "experiment": "followup_model_error_analysis_2026_07_15",
        "scope": "v1",
        "model_primary": PRIMARY_MODEL,
        "model_fallback": FALLBACK_MODEL,
        "chunk_size": CHUNK_SIZE,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "v1_allocation": V1_PLAN,
        "v2_cost_approval": False,
        "llm_cost_summary": summary,
        "updated_at": _now(),
    }
    _atomic_write_text(
        EXPERIMENT_DIR / "outputs" / "run_manifest.json",
        json.dumps(manifest, indent=2) + "\n",
    )

    _append_progress(
        f"## [{_now()}] Phase 2 — extraction finished\n\n"
        f"- Status: completed\n"
        f"- Scope: v1\n"
        f"- Details: new_calls={total_new} skipped={total_skipped} "
        f"planned={planned_calls} total_cost_usd={summary['total_cost_usd']}\n"
        f"- Artifacts: `outputs/llm_features/cost_summary.json`, "
        f"`outputs/run_manifest.json`\n"
        f"- Cost (if LLM phase): cumulative_usd={summary['total_cost_usd']} "
        f"new_calls={total_new} skipped={total_skipped} planned={planned_calls}"
    )
    print(json.dumps(summary, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="V1-safe LLM feature extraction")
    p.add_argument("--scope", choices=["v1", "v2", "full"], default="v1")
    p.add_argument("--max-calls", type=int, default=20)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--i-approve-v2-cost",
        action="store_true",
        help="Required for --scope v2/full after explicit ~$140 approval",
    )
    p.add_argument("--serial-buckets", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.scope in {"v2", "full"} and not args.i_approve_v2_cost:
        raise SystemExit(
            "Refusing V2/full (~$140 extraction). Need --i-approve-v2-cost after "
            "explicit user cost approval."
        )
    run_extraction(
        scope="v1" if args.scope == "v1" else args.scope,
        max_calls=args.max_calls,
        dry_run=args.dry_run,
        approve_v2=args.i_approve_v2_cost,
        parallel_buckets=not args.serial_buckets,
    )


if __name__ == "__main__":
    main()
