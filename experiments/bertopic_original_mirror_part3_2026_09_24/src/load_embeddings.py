"""Cache Titan embeddings for every Part 2+3 union stimulus post.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py \\
      --text-role original --refresh-from-identity-cache --backfill
"""

from __future__ import annotations

import argparse
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import (
    N_STIMULI_EXPECTED,
    select_text_column,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    AWS_REGION as BEDROCK_AWS_REGION,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3
from shared.embeddings.bedrock import BEDROCK_MODEL_ID, EMBEDDING_DIMENSIONS, create_embedding

N_EXPECTED = N_STIMULI_EXPECTED
CORPUS_NAME = "study_phase_2_part_2_and_3_stimuli_full"
EMBED_ROLES = frozenset({"original", "mirror"})
DISK_CACHE_DIRNAME = ".identity_disk_cache"
EMBEDDINGS_FILENAME = "embeddings.npy"
INDEX_FILENAME = "index.parquet"
METADATA_FILENAME = "metadata.json"
SOURCE_LOCAL = "local_cache"
SOURCE_IDENTITY = "identity_cache"
SOURCE_MIXED = "mixed_identity_and_bedrock"
SOURCE_SEED_MIXED = "mixed_local_seed_and_identity"
PROVENANCE_REUSED_LOCAL = "reused_local"
PROVENANCE_IDENTITY = "identity"
PROVENANCE_BACKFILLED = "backfilled"
RESOLVE_WORKERS = 16
BACKFILL_ATTEMPTS = 5
_VECTOR_CACHE_LOCK = threading.Lock()

METADATA_KEYS = (
    "text_role",
    "model_id",
    "dimensions",
    "normalize",
    "n_rows",
    "n_expected",
    "source",
    "ddb_table",
    "dropped_post_ids",
    "backfill_post_ids",
    "corpus",
    "dedupe_applied",
    "provenance",
)


@dataclass(frozen=True)
class EmbeddingCacheResult:
    """Summary of one role cache."""

    cache_dir: Path
    n_rows: int
    n_backfilled: int
    source: str
    provenance: dict[str, int] | None = None


def require_embed_role(role: str) -> str:
    """Return ``role`` when it is original or mirror.

    Raises
    ------
    ValueError
        If ``role`` is joint or unknown.
    """
    if role not in EMBED_ROLES:
        raise ValueError(f"Embedding role must be original or mirror, got {role!r}")
    return role


def select_text_for_role(posts: pd.DataFrame, role: str) -> pd.Series:
    """Return the text series embedded for ``role``.

    Parameters
    ----------
    posts
        Stimulus frame from ``load_stimuli_posts``.
    role
        ``original`` or ``mirror``.

    Returns
    -------
    pandas.Series
        Text aligned to ``posts``.
    """
    return posts[select_text_column(require_embed_role(role))].astype(str)


def order_posts(posts: pd.DataFrame) -> pd.DataFrame:
    """Return posts sorted by ``post_id`` ascending."""
    return posts.sort_values("post_id", kind="mergesort").reset_index(drop=True)


def build_index(post_ids: list[str]) -> pd.DataFrame:
    """Return a ``row_id`` / ``post_id`` index in ascending post id order."""
    ordered = sorted(post_ids)
    return pd.DataFrame({"row_id": np.arange(len(ordered), dtype=np.int64), "post_id": ordered})


def assert_full_coverage(n_rows: int, n_expected: int, dropped_post_ids: list[str], role: str) -> None:
    """Raise when a role cache is short of the stimulus catalog.

    Raises
    ------
    RuntimeError
        If ``n_rows`` differs from ``n_expected`` or any post was dropped.
    """
    if n_rows == n_expected and not dropped_post_ids:
        return
    preview = dropped_post_ids[:5]
    raise RuntimeError(
        f"Titan embedding coverage {n_rows}/{n_expected} for role={role}; dropped={preview}"
    )


def cache_file_paths(cache_dir: Path) -> tuple[Path, Path, Path]:
    """Return embeddings, index, and metadata paths inside ``cache_dir``."""
    return (
        cache_dir / EMBEDDINGS_FILENAME,
        cache_dir / INDEX_FILENAME,
        cache_dir / METADATA_FILENAME,
    )


def write_cache(cache_dir: Path, embeddings: np.ndarray, index: pd.DataFrame, metadata: dict) -> None:
    """Atomically write the three cache files."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(cache_dir)) as tmp:
        tmp_dir = Path(tmp)
        emb_tmp = tmp_dir / EMBEDDINGS_FILENAME
        index_tmp = tmp_dir / INDEX_FILENAME
        meta_tmp = tmp_dir / METADATA_FILENAME
        np.save(emb_tmp, embeddings)
        index.to_parquet(index_tmp, index=False)
        meta_tmp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        emb_path, index_path, meta_path = cache_file_paths(cache_dir)
        emb_tmp.replace(emb_path)
        index_tmp.replace(index_path)
        meta_tmp.replace(meta_path)


def build_titan_metadata(
    role: str,
    n_rows: int,
    source: str,
    dropped_post_ids: list[str],
    backfill_post_ids: list[str],
    n_expected: int = N_EXPECTED,
    provenance: dict[str, int] | None = None,
) -> dict:
    """Return the Titan cache metadata document."""
    return {
        "text_role": role,
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
        "n_rows": n_rows,
        "n_expected": n_expected,
        "source": source,
        "ddb_table": DYNAMODB_TABLE_NAME,
        "dropped_post_ids": dropped_post_ids,
        "backfill_post_ids": backfill_post_ids,
        "corpus": CORPUS_NAME,
        "dedupe_applied": False,
        "provenance": provenance or {
            PROVENANCE_REUSED_LOCAL: 0,
            PROVENANCE_IDENTITY: n_rows,
            PROVENANCE_BACKFILLED: len(backfill_post_ids),
        },
    }


def vectors_match(left: np.ndarray, right: np.ndarray) -> bool:
    """Return True when two Titan vectors are numerically identical."""
    return bool(np.allclose(left.ravel(), right.ravel(), rtol=0.0, atol=1e-8))


def read_role_cache_vectors(cache_dir: Path, dimensions: int = EMBEDDING_DIMENSIONS) -> dict[str, np.ndarray]:
    """Load ``post_id`` → vector from a role cache directory."""
    emb_path, index_path, _ = cache_file_paths(cache_dir)
    if not (emb_path.is_file() and index_path.is_file()):
        raise FileNotFoundError(f"Incomplete cache at {cache_dir}")
    index = pd.read_parquet(index_path)
    embeddings = np.load(emb_path)
    if embeddings.shape != (len(index), dimensions):
        raise ValueError(
            f"Cache shape mismatch: embeddings={embeddings.shape} index_rows={len(index)}"
        )
    by_post: dict[str, np.ndarray] = {}
    for row_id, post_id in zip(index["row_id"].astype(int), index["post_id"].astype(str)):
        by_post[post_id] = np.asarray(embeddings[int(row_id)], dtype=np.float64).ravel()
    return by_post


def infer_titan_source(provenance: dict[str, int]) -> str:
    """Map provenance counts to a metadata ``source`` label."""
    if provenance.get(PROVENANCE_BACKFILLED, 0) > 0:
        return SOURCE_MIXED
    if provenance.get(PROVENANCE_REUSED_LOCAL, 0) > 0:
        return SOURCE_SEED_MIXED
    return SOURCE_IDENTITY


def resolve_single_post_vector(
    post_id: str,
    text: str,
    backfill: bool,
    seed_vectors: dict[str, np.ndarray] | None,
    ddb: DynamoDBEmbeddingIndex,
    s3: S3,
    disk_cache_root: Path,
    embedding_id_to_vec: dict[str, np.ndarray],
) -> tuple[np.ndarray | None, str]:
    """Resolve one Titan vector and its provenance label."""
    seed_vec = seed_vectors.get(post_id) if seed_vectors else None
    identity_vec = fetch_identity_vector(text, ddb, s3, disk_cache_root, embedding_id_to_vec)
    if seed_vec is not None:
        if identity_vec is not None:
            if vectors_match(seed_vec, identity_vec):
                return seed_vec, PROVENANCE_REUSED_LOCAL
            return identity_vec, PROVENANCE_IDENTITY
        return seed_vec, PROVENANCE_REUSED_LOCAL
    if identity_vec is not None:
        return identity_vec, PROVENANCE_IDENTITY
    if not backfill:
        return None, "dropped"
    try:
        return backfill_embedding(text), PROVENANCE_BACKFILLED
    except Exception:
        return None, "dropped"


def _disk_cache_path(disk_cache_root: Path, embedding_id: str) -> Path:
    return disk_cache_root / "embeddings" / f"{embedding_id}.npy"


def fetch_identity_vector(
    text: str,
    ddb: DynamoDBEmbeddingIndex,
    s3: S3,
    disk_cache_root: Path,
    embedding_id_to_vec: dict[str, np.ndarray],
) -> np.ndarray | None:
    """Return one Titan vector from disk or DynamoDB+S3, or None if missing."""
    embedding_id = embedding_identity_sha256(
        text,
        model_id=BEDROCK_MODEL_ID,
        dimensions=EMBEDDING_DIMENSIONS,
        normalize=True,
    )
    with _VECTOR_CACHE_LOCK:
        if embedding_id in embedding_id_to_vec:
            return embedding_id_to_vec[embedding_id]
    cached = _disk_cache_path(disk_cache_root, embedding_id)
    if cached.exists():
        vec = np.load(cached)
        embedding_id_to_vec[embedding_id] = vec
        return vec
    row = ddb.get_item(embedding_id)
    if row is None:
        return None
    s3_key = str(row.get("s3_key", "")).strip()
    if not s3_key:
        return None
    parsed = json.loads(s3.get_bytes(s3_key).decode("utf-8"))
    values = parsed.get("embedding")
    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSIONS:
        return None
    vec = np.asarray([float(value) for value in values], dtype=np.float64)
    cached.parent.mkdir(parents=True, exist_ok=True)
    np.save(cached, vec)
    with _VECTOR_CACHE_LOCK:
        embedding_id_to_vec[embedding_id] = vec
    return vec


def backfill_embedding(text: str) -> np.ndarray:
    """Call Bedrock for one text, retrying transient failures."""
    import time

    last_error: Exception | None = None
    for attempt in range(BACKFILL_ATTEMPTS):
        try:
            payload = create_embedding(text)
            values = payload["embedding"]
            if len(values) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(f"Unexpected embedding length {len(values)}")
            return np.asarray(values, dtype=np.float64)
        except Exception as exc:  # noqa: BLE001 - retry then surface the last error
            last_error = exc
            time.sleep(min(2**attempt, 16))
    raise RuntimeError(f"Bedrock backfill failed: {last_error}")


def _resolve_one(
    post_id: str,
    text: str,
    backfill: bool,
    seed_vectors: dict[str, np.ndarray] | None,
    ddb: DynamoDBEmbeddingIndex,
    s3: S3,
    disk_cache_root: Path,
    embedding_id_to_vec: dict[str, np.ndarray],
) -> tuple[str, np.ndarray | None, str]:
    """Return post id, vector, and provenance label."""
    vector, provenance = resolve_single_post_vector(
        post_id,
        text,
        backfill,
        seed_vectors,
        ddb,
        s3,
        disk_cache_root,
        embedding_id_to_vec,
    )
    if vector is None:
        return post_id, None, provenance
    return post_id, np.asarray(vector, dtype=np.float64).ravel(), provenance


def resolve_role_vectors(
    posts: pd.DataFrame,
    role: str,
    backfill: bool,
    seed_dir: Path | None = None,
) -> tuple[np.ndarray, pd.DataFrame, list[str], list[str], dict[str, int]]:
    """Resolve Titan vectors for ``posts`` in post-id order.

    Returns
    -------
    tuple
        Embeddings, index, dropped post ids, backfilled post ids, provenance counts.
    """
    ordered = order_posts(posts)
    texts = select_text_for_role(ordered, role).tolist()
    post_ids = ordered["post_id"].astype(str).tolist()
    seed_vectors = read_role_cache_vectors(seed_dir) if seed_dir is not None else None
    disk_cache = paths.EXPERIMENT_ROOT / "outputs" / "embeddings" / DISK_CACHE_DIRNAME
    disk_cache.mkdir(parents=True, exist_ok=True)
    s3 = S3(S3_BUCKET, region_name=BEDROCK_AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(DYNAMODB_TABLE_NAME, region_name=BEDROCK_AWS_REGION)
    shared_vectors: dict[str, np.ndarray] = {}
    jobs = [
        (post_id, text, backfill, seed_vectors, ddb, s3, disk_cache, shared_vectors)
        for post_id, text in zip(post_ids, texts)
    ]
    resolved: list[tuple[str, np.ndarray | None, str]] = []
    with ThreadPoolExecutor(max_workers=RESOLVE_WORKERS) as pool:
        iterator = pool.map(lambda job: _resolve_one(*job), jobs)
        resolved = list(tqdm(iterator, total=len(jobs), desc=f"Titan {role}", unit="post"))
    return _stack_resolved(resolved)


def _stack_resolved(
    resolved: list[tuple[str, np.ndarray | None, str]],
) -> tuple[np.ndarray, pd.DataFrame, list[str], list[str], dict[str, int]]:
    """Stack successful vectors and list drops, backfills, and provenance."""
    vectors: list[np.ndarray] = []
    kept: list[str] = []
    dropped: list[str] = []
    backfilled: list[str] = []
    provenance_counts = {
        PROVENANCE_REUSED_LOCAL: 0,
        PROVENANCE_IDENTITY: 0,
        PROVENANCE_BACKFILLED: 0,
    }
    for post_id, vector, label in resolved:
        if vector is None:
            dropped.append(post_id)
            continue
        vectors.append(vector)
        kept.append(post_id)
        if label == PROVENANCE_BACKFILLED:
            backfilled.append(post_id)
        if label in provenance_counts:
            provenance_counts[label] += 1
    if not vectors:
        empty = np.zeros((0, EMBEDDING_DIMENSIONS), dtype=np.float64)
        return empty, build_index([]), dropped, backfilled, provenance_counts
    order = np.argsort(np.array(kept))
    ordered_ids = [kept[int(position)] for position in order]
    embeddings = np.vstack([vectors[int(position)] for position in order])
    return embeddings, build_index(ordered_ids), dropped, backfilled, provenance_counts


def local_cache_is_complete(cache_dir: Path, post_ids: set[str], role: str) -> bool:
    """Return True when the local cache covers every post id for ``role``."""
    emb_path, index_path, meta_path = cache_file_paths(cache_dir)
    if not (emb_path.is_file() and index_path.is_file() and meta_path.is_file()):
        return False
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if metadata.get("model_id") != BEDROCK_MODEL_ID:
        return False
    if int(metadata.get("dimensions", -1)) != EMBEDDING_DIMENSIONS:
        return False
    if metadata.get("text_role") != role or metadata.get("dedupe_applied") is not False:
        return False
    index = pd.read_parquet(index_path)
    embeddings = np.load(emb_path)
    if embeddings.shape != (len(index), EMBEDDING_DIMENSIONS):
        return False
    return post_ids.issubset(set(index["post_id"].astype(str))) and not metadata.get("dropped_post_ids")


def load_local_cache(cache_dir: Path) -> EmbeddingCacheResult:
    """Load a complete local cache without calling AWS."""
    emb_path, index_path, meta_path = cache_file_paths(cache_dir)
    embeddings = np.load(emb_path)
    index = pd.read_parquet(index_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if embeddings.shape != (len(index), EMBEDDING_DIMENSIONS):
        raise ValueError(f"Cache shape mismatch: embeddings={embeddings.shape} index_rows={len(index)}")
    provenance = metadata.get("provenance")
    return EmbeddingCacheResult(
        cache_dir=cache_dir,
        n_rows=len(index),
        n_backfilled=len(metadata.get("backfill_post_ids", [])),
        source=SOURCE_LOCAL,
        provenance=provenance if isinstance(provenance, dict) else None,
    )


def run_load_embeddings(
    role: str,
    refresh_from_identity_cache: bool,
    backfill: bool,
    seed_from_local_cache: Path | None = None,
) -> EmbeddingCacheResult:
    """Build or load the Titan cache for one text role.

    Parameters
    ----------
    role
        ``original`` or ``mirror``.
    refresh_from_identity_cache
        Rebuild from DynamoDB+S3 even when a local cache exists.
    backfill
        Call Bedrock for texts missing from the identity cache.

    Returns
    -------
    EmbeddingCacheResult
        Written or loaded cache summary.
    """
    validated = require_embed_role(role)
    posts = data_mod.load_stimuli_posts()
    post_ids = set(posts["post_id"].astype(str))
    cache_dir = paths.embeddings_dir(validated)
    if (
        not refresh_from_identity_cache
        and seed_from_local_cache is None
        and local_cache_is_complete(cache_dir, post_ids, validated)
    ):
        result = load_local_cache(cache_dir)
    else:
        result = _resolve_and_write(
            posts,
            validated,
            backfill,
            cache_dir,
            seed_from_local_cache=seed_from_local_cache,
        )
    provenance_msg = ""
    if result.provenance:
        provenance_msg = f" provenance={result.provenance}"
    print(
        f"n_rows={result.n_rows} n_expected={N_EXPECTED} n_backfilled={result.n_backfilled} "
        f"source={result.source}{provenance_msg} cache_path={result.cache_dir}"
    )
    return result


def _resolve_and_write(
    posts: pd.DataFrame,
    role: str,
    backfill: bool,
    cache_dir: Path,
    seed_from_local_cache: Path | None = None,
) -> EmbeddingCacheResult:
    """Resolve vectors, reject partial coverage, and write the cache."""
    embeddings, index, dropped, backfilled, provenance = resolve_role_vectors(
        posts,
        role,
        backfill,
        seed_dir=seed_from_local_cache,
    )
    assert_full_coverage(len(index), N_EXPECTED, dropped, role)
    source = infer_titan_source(provenance)
    metadata = build_titan_metadata(
        role,
        len(index),
        source,
        dropped,
        backfilled,
        provenance=provenance,
    )
    write_cache(cache_dir, embeddings, index, metadata)
    return EmbeddingCacheResult(
        cache_dir,
        len(index),
        len(backfilled),
        source,
        provenance=provenance,
    )


def main() -> None:
    """CLI entry for the Titan cache."""
    parser = argparse.ArgumentParser(description="Cache Titan embeddings for Part 2+3 union stimuli.")
    parser.add_argument("--text-role", choices=sorted(EMBED_ROLES), required=True)
    parser.add_argument("--refresh-from-identity-cache", action="store_true")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument(
        "--seed-from-local-cache",
        type=Path,
        default=None,
        help="Reuse vectors from an existing on-disk role cache when post_id and text identity match.",
    )
    args = parser.parse_args()
    run_load_embeddings(
        args.text_role,
        args.refresh_from_identity_cache,
        args.backfill,
        seed_from_local_cache=args.seed_from_local_cache,
    )


if __name__ == "__main__":
    main()
