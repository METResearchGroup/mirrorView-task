"""Compute OpenAI embeddings for unique text instances and write Parquet artifacts."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI

from experiments.mirrors_content_analysis_2026_04_24.dataloader import (
    Dataloader as MirrorViewPilotDataloader,
)
from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from experiments.predict_keep_remove_2026_05_07.embeddings.instances import (
    TEXT_ROLE_MIRROR,
    TEXT_ROLE_ORIGINAL,
    build_text_instances_table,
)


def l2_normalize_vector(vec: list[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in vec))
    if s == 0.0:
        return vec
    return [float(x / s) for x in vec]


def _embed_batch_with_retry(
    client: OpenAI,
    *,
    model: str,
    inputs: list[str],
    max_retries: int = 10,
    initial_delay_s: float = 1.0,
) -> tuple[list[list[float]], int]:
    """Return embeddings in request order and total prompt tokens (if reported)."""
    delay = initial_delay_s
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(model=model, input=inputs)
            ordered = sorted(resp.data, key=lambda d: d.index)
            vectors = [list(map(float, d.embedding)) for d in ordered]
            usage = getattr(resp, "usage", None)
            tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
            return vectors, tokens
        except Exception as exc:  # noqa: BLE001 — retry broad API errors
            last_exc = exc
            if attempt >= max_retries - 1:
                break
            time.sleep(delay)
            delay = min(delay * 2.0, 120.0)
    assert last_exc is not None
    raise last_exc


@dataclass(frozen=True)
class EmbeddingRunResult:
    output_dir: Path
    metadata_path: Path
    n_text_instances: int
    n_unique_text_hashes: int
    n_embedded_new: int
    n_reused_from_cache: int
    text_instances_path: Path | None = None
    embeddings_text_instances_path: Path | None = None
    original_sidecar_path: Path | None = None
    mirrors_sidecar_path: Path | None = None


def _load_hash_cache(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    required = {"text_hash", "embedding_model", "embedding", "embedding_dim"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Cache parquet missing columns: {sorted(missing)}")
    return df


def _dedupe_hash_cache(df: pd.DataFrame) -> pd.DataFrame:
    """Keep latest row per (embedding_model, text_hash) by created_at if present."""
    out = df.copy()
    if "created_at" in out.columns:
        out = out.sort_values(["embedding_model", "text_hash", "created_at"])
    return out.drop_duplicates(subset=["embedding_model", "text_hash"], keep="last")


def run_embedding_pipeline(
    *,
    output_dir: Path,
    embedding_model: str,
    batch_size: int,
    input_cache_path: Path | None,
    write_cache_path: Path | None,
    l2_normalize: bool,
    dry_run: bool,
    omit_text_column: bool,
    openai_client: OpenAI | None = None,
) -> EmbeddingRunResult:
    """Load training rows, embed unique texts, write Parquet + metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = Dataloader()
    df = loader.load_training_dataframe()
    instances = build_text_instances_table(df)

    if omit_text_column:
        instances_out = instances.drop(columns=["text"]).copy()
    else:
        instances_out = instances.copy()

    now = datetime.now(timezone.utc)
    created_iso = now.isoformat()

    per_hash = (
        instances.groupby("text_hash", as_index=False)
        .first()[["text_hash", "text"]]
        .copy()
    )
    n_unique = len(per_hash)

    cache_all: pd.DataFrame | None = None
    if input_cache_path is not None and input_cache_path.is_file():
        cache_all = _dedupe_hash_cache(_load_hash_cache(input_cache_path))

    empty_cols = ["text_hash", "embedding_model", "embedding_dim", "embedding", "created_at"]
    model_cache = pd.DataFrame(columns=empty_cols)
    if cache_all is not None and len(cache_all):
        model_cache = cache_all.loc[
            cache_all["embedding_model"] == embedding_model
        ].copy()

    needed_hashes = set(instances["text_hash"].tolist())
    known_hashes = set(model_cache["text_hash"].tolist()) if len(model_cache) else set()
    missing_hashes = sorted(needed_hashes - known_hashes)
    n_reused = len(needed_hashes & known_hashes)

    new_rows: list[dict[str, Any]] = []
    total_prompt_tokens = 0

    if dry_run:
        text_path = output_dir / "text_instances.parquet"
        instances.to_parquet(text_path, index=False)
        mv = MirrorViewPilotDataloader()
        mv.get_latest_mirrorview_run_data()
        source_export = (
            str(mv.last_loaded_export_path) if mv.last_loaded_export_path else None
        )
        metadata = {
            "created_at": created_iso,
            "embedding_model": embedding_model,
            "batch_size": batch_size,
            "l2_normalize": l2_normalize,
            "dry_run": True,
            "omit_text_column": omit_text_column,
            "source_export_csv": source_export,
            "output_dir": str(output_dir.resolve()),
            "text_instances_parquet": str(text_path.resolve()),
            "n_training_rows": int(len(df)),
            "n_text_instance_rows": int(len(instances)),
            "n_unique_text_hashes": int(n_unique),
            "n_embedded_new": 0,
            "n_reused_from_cache": int(n_reused),
            "openai_prompt_tokens_est": 0,
            "input_cache_path": str(input_cache_path) if input_cache_path else None,
            "write_cache_path": str(write_cache_path) if write_cache_path else None,
        }
        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return EmbeddingRunResult(
            output_dir=output_dir,
            metadata_path=metadata_path,
            n_text_instances=len(instances),
            n_unique_text_hashes=n_unique,
            n_embedded_new=0,
            n_reused_from_cache=n_reused,
            text_instances_path=text_path,
        )

    if missing_hashes:
        client = openai_client or OpenAI()
        hash_to_text = dict(zip(per_hash["text_hash"], per_hash["text"], strict=True))
        for i in range(0, len(missing_hashes), batch_size):
            batch_hashes = missing_hashes[i : i + batch_size]
            batch_texts = [hash_to_text[h] for h in batch_hashes]
            vectors, batch_tokens = _embed_batch_with_retry(
                client, model=embedding_model, inputs=batch_texts
            )
            total_prompt_tokens += batch_tokens
            for h, vec in zip(batch_hashes, vectors, strict=True):
                if l2_normalize:
                    vec = l2_normalize_vector(vec)
                new_rows.append(
                    {
                        "text_hash": h,
                        "embedding_model": embedding_model,
                        "embedding_dim": len(vec),
                        "embedding": vec,
                        "created_at": created_iso,
                    }
                )

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        model_cache = pd.concat([model_cache, new_df], ignore_index=True)
        model_cache = _dedupe_hash_cache(model_cache)

    if len(model_cache) == 0:
        raise RuntimeError(
            "No embeddings available (empty cache and no successful embedding calls)."
        )

    merged_on_hash = instances_out.merge(
        model_cache,
        on="text_hash",
        how="left",
        validate="m:1",
    )
    if merged_on_hash["embedding"].isna().any():
        bad = merged_on_hash.loc[merged_on_hash["embedding"].isna(), ["post_id", "text_role", "text_hash"]]
        raise RuntimeError(
            "Some text instances are missing embeddings after cache/API merge:\n"
            f"{bad.head(20).to_string(index=False)}"
        )

    embeddings_path = output_dir / "embeddings_text_instances.parquet"
    merged_on_hash.to_parquet(embeddings_path, index=False)

    orig_side = output_dir / "original_text.parquet"
    mirr_side = output_dir / "mirrors.parquet"
    merged_on_hash.loc[merged_on_hash["text_role"] == TEXT_ROLE_ORIGINAL].to_parquet(
        orig_side, index=False
    )
    merged_on_hash.loc[merged_on_hash["text_role"] == TEXT_ROLE_MIRROR].to_parquet(
        mirr_side, index=False
    )

    if write_cache_path is not None and len(model_cache):
        write_cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_all is not None:
            other = cache_all.loc[
                cache_all["embedding_model"] != embedding_model
            ].copy()
            combined = pd.concat([other, model_cache], ignore_index=True)
        else:
            combined = model_cache
        combined = _dedupe_hash_cache(combined)
        combined.to_parquet(write_cache_path, index=False)

    mv = MirrorViewPilotDataloader()
    mv.get_latest_mirrorview_run_data()
    source_export = str(mv.last_loaded_export_path) if mv.last_loaded_export_path else None

    metadata = {
        "created_at": created_iso,
        "embedding_model": embedding_model,
        "batch_size": batch_size,
        "l2_normalize": l2_normalize,
        "dry_run": False,
        "omit_text_column": omit_text_column,
        "source_export_csv": source_export,
        "output_dir": str(output_dir.resolve()),
        "embeddings_text_instances_parquet": str(embeddings_path.resolve()),
        "original_text_parquet": str(orig_side.resolve()),
        "mirrors_parquet": str(mirr_side.resolve()),
        "n_training_rows": int(len(df)),
        "n_text_instance_rows": int(len(instances)),
        "n_unique_text_hashes": int(n_unique),
        "n_embedded_new": int(len(missing_hashes)),
        "n_reused_from_cache": int(n_reused),
        "openai_prompt_tokens_est": int(total_prompt_tokens),
        "input_cache_path": str(input_cache_path) if input_cache_path else None,
        "write_cache_path": str(write_cache_path) if write_cache_path else None,
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return EmbeddingRunResult(
        output_dir=output_dir,
        metadata_path=metadata_path,
        n_text_instances=len(instances),
        n_unique_text_hashes=n_unique,
        n_embedded_new=len(missing_hashes),
        n_reused_from_cache=n_reused,
        embeddings_text_instances_path=embeddings_path,
        original_sidecar_path=orig_side,
        mirrors_sidecar_path=mirr_side,
    )
