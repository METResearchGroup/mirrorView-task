"""Feature construction, embedding joins, preprocessing, and evaluation metrics."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OneHotEncoder

from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    AWS_REGION,
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
)
from experiments.simplified_predict_remove_2026_05_13.generate_embeddings import (
    TEXT_ROLE_MIRROR,
    TEXT_ROLE_ORIGINAL,
    validate_post_ids_unique,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3

JOIN_COL_ORIGINAL = "embedding_original_text"
JOIN_COL_MIRROR = "embedding_mirror_text"
CAT_COLUMNS: tuple[str, str] = ("sampled_stance", "sampled_toxicity")


def embedding_lookup_from_rows(
    embedding_rows: list[Any],
    *,
    key_post_id_role: tuple[str, str] = ("post_id", "text_role"),
    vector_attr: str = "embedding_vector",
) -> MutableMapping[tuple[str, str], list[float]]:
    """Build ``(post_id, text_role) -> vector`` from ``EmbeddingInstanceRow``-like objects."""
    out: dict[tuple[str, str], list[float]] = {}
    pk, rk = key_post_id_role
    for er in embedding_rows:
        pid = str(getattr(er, pk))
        role = str(getattr(er, rk))
        vec = getattr(er, vector_attr)
        out[(pid, role)] = [float(x) for x in vec]
    return out


def join_embeddings(
    df: pd.DataFrame,
    lookup: Mapping[tuple[str, str], Sequence[float]],
) -> pd.DataFrame:
    """Add ``JOIN_COL_ORIGINAL`` and ``JOIN_COL_MIRROR`` ndarray columns."""
    out = df.copy()

    if "post_id" not in out.columns:
        raise KeyError("post_id")

    validate_post_ids_unique(out)

    missing: list[str] = []

    oid: list[np.ndarray] = []
    mid: list[np.ndarray] = []
    for _, row in out.iterrows():
        pid = str(row["post_id"])
        ko = (pid, TEXT_ROLE_ORIGINAL)
        km = (pid, TEXT_ROLE_MIRROR)

        vo = lookup.get(ko)
        vm = lookup.get(km)

        errs: list[str] = []
        if vo is None:
            errs.append(f"missing_original:{ko}")
        if vm is None:
            errs.append(f"missing_mirror:{km}")
        if errs:
            missing.append(f"post_id={pid}: " + ", ".join(errs))
            continue

        oid.append(np.asarray(vo, dtype=np.float64))
        mid.append(np.asarray(vm, dtype=np.float64))

    if missing:
        preview = "; ".join(missing[:15])
        more = ""
        if len(missing) > 15:
            more = f" (+{len(missing) - 15} more)"
        raise KeyError(f"Embedding lookup misses {len(missing)} rows: {preview}{more}")

    out[JOIN_COL_ORIGINAL] = oid
    out[JOIN_COL_MIRROR] = mid
    return out


def _fetch_embedding_by_text(
    text: str,
    *,
    s3: S3,
    ddb: DynamoDBEmbeddingIndex,
    model_id: str,
    dimensions: int,
    normalize: bool,
) -> list[float]:
    eid = embedding_identity_sha256(
        text,
        model_id=model_id,
        dimensions=dimensions,
        normalize=normalize,
    )
    d_row = ddb.get_item(eid)
    if d_row is None:
        raise KeyError(f"No DynamoDB embedding row for embedding_id={eid!r}")

    key = str(d_row.get("s3_key", ""))
    if not key.strip():
        raise KeyError(f"s3_key missing from DynamoDB row {eid!r}")

    raw = s3.get_bytes(key)
    parsed = json.loads(raw.decode("utf-8"))
    emb = parsed.get("embedding")
    if emb is None or not isinstance(emb, list):
        raise RuntimeError(f"S3 embedding invalid for embedding_id={eid!r}")
    return [float(x) for x in emb]


def load_embeddings_via_dynamodb_and_s3(
    df: pd.DataFrame,
    *,
    bucket: str | None = None,
    table: str | None = None,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
) -> Mapping[tuple[str, str], list[float]]:
    """Fetch embeddings for ``df`` rows from S3 pointers in DynamoDB (identity key)."""
    validate_post_ids_unique(df)
    for c in ("original_text", "mirror_text"):
        if c not in df.columns:
            raise KeyError(c)

    b = (bucket or S3_BUCKET).strip()
    t = (table or DYNAMODB_TABLE_NAME).strip()
    s3 = S3(b, region_name=AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(t, region_name=AWS_REGION)

    lookup: dict[tuple[str, str], list[float]] = {}

    def put(pid: str, role: str, text: str) -> None:
        key = (str(pid), str(role))
        if key in lookup:
            return
        vec = _fetch_embedding_by_text(
            text,
            s3=s3,
            ddb=ddb,
            model_id=model_id,
            dimensions=dimensions,
            normalize=normalize,
        )
        lookup[key] = vec

    for _, r in df.iterrows():
        pid = str(r["post_id"])
        put(pid, TEXT_ROLE_ORIGINAL, str(r["original_text"]))
        put(pid, TEXT_ROLE_MIRROR, str(r["mirror_text"]))

    return lookup


def stack_embedding_dense_block(orig: np.ndarray, mirror: np.ndarray) -> np.ndarray:
    """Original, mirror, |o-m|, o*m, cosine(o,m)."""
    o = np.asarray(orig, dtype=np.float64).ravel()
    m = np.asarray(mirror, dtype=np.float64).ravel()
    if o.shape != m.shape:
        raise ValueError(f"embedding length mismatch original={len(o)} mirror={len(m)}")
    diff = np.abs(o - m)
    prod = o * m
    denom = float(np.linalg.norm(o) * np.linalg.norm(m))
    cos = float(np.dot(o, m) / denom) if denom > 0.0 else 0.0
    return np.concatenate([o, m, diff, prod, np.array([cos], dtype=np.float64)])


def embedding_dense_column_names(dim: int) -> list[str]:
    names: list[str] = []
    names += [f"orig_{i}" for i in range(dim)]
    names += [f"mirror_{i}" for i in range(dim)]
    names += [f"abs_diff_{i}" for i in range(dim)]
    names += [f"elem_prod_{i}" for i in range(dim)]
    names.append("cosine_similarity")
    return names


class EmbeddingMetadataMatrixBuilder:
    """Fit one-hot categorical metadata on train; transform train/test without leakage."""

    def __init__(self) -> None:
        enc = OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False,
        )
        self._column_transformer = ColumnTransformer(
            [("cats", enc, list(CAT_COLUMNS))],
            remainder="drop",
        )
        self._embedding_dim: int | None = None
        self._dense_names: list[str] | None = None
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> EmbeddingMetadataMatrixBuilder:
        missing = [c for c in CAT_COLUMNS if c not in df.columns]
        if missing:
            raise KeyError(f"Missing categorical columns: {missing}")

        req = (JOIN_COL_ORIGINAL, JOIN_COL_MIRROR)
        for c in req:
            if c not in df.columns:
                raise KeyError(c)

        self._embedding_dim = int(np.asarray(df[JOIN_COL_ORIGINAL].iloc[0]).shape[0])
        self._dense_names = embedding_dense_column_names(self._embedding_dim)

        blk0 = stack_embedding_dense_block(
            df[JOIN_COL_ORIGINAL].iloc[0],
            df[JOIN_COL_MIRROR].iloc[0],
        )
        expected = 4 * self._embedding_dim + 1
        if blk0.shape[0] != expected:
            raise RuntimeError(f"Dense block sizing bug: expected {expected} got {blk0.shape[0]}")

        self._column_transformer.fit(df.loc[:, CAT_COLUMNS])
        self._fitted = True
        return self

    @property
    def feature_names_(self) -> list[str]:
        if not self._fitted or self._dense_names is None:
            raise RuntimeError("Call fit() before reading feature_names_")
        ohe = self._column_transformer.named_transformers_["cats"]
        assert isinstance(ohe, OneHotEncoder)
        oh = list(ohe.get_feature_names_out(CAT_COLUMNS))
        return list(self._dense_names) + oh

    def transform(self, df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        if not self._fitted or self._dense_names is None:
            raise RuntimeError("Call fit() before transform.")
        mats = [
            stack_embedding_dense_block(row[JOIN_COL_ORIGINAL], row[JOIN_COL_MIRROR])
            for _, row in df.iterrows()
        ]
        stacked = np.vstack(mats)
        oh_part = self._column_transformer.transform(df.loc[:, CAT_COLUMNS])
        x = np.hstack([stacked.astype(np.float64), oh_part.astype(np.float64)])
        return x, self.feature_names_


def build_xy(
    df: pd.DataFrame,
    builder: EmbeddingMetadataMatrixBuilder,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Produce feature matrix ``X``, label ``y``, and aligned names."""
    if "keep_remove_label" not in df.columns:
        raise KeyError("keep_remove_label")
    if JOIN_COL_ORIGINAL not in df.columns or JOIN_COL_MIRROR not in df.columns:
        raise KeyError("join embeddings first with join_embeddings(...)")

    x, fn = builder.transform(df)
    y = df["keep_remove_label"].astype(np.int64).values
    return x, y, fn


def classification_metrics_summary(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    pos_scores: Sequence[float],
) -> dict[str, float]:
    y_t = np.asarray(y_true).astype(np.int64)
    y_p = np.asarray(y_pred).astype(np.int64)
    s = np.asarray(pos_scores).astype(np.float64)

    out: dict[str, float] = {
        "accuracy": float(accuracy_score(y_t, y_p)),
        "precision": float(precision_score(y_t, y_p, zero_division=0)),
        "recall": float(recall_score(y_t, y_p, zero_division=0)),
        "f1": float(f1_score(y_t, y_p, zero_division=0)),
    }

    def _maybe(fn: Any) -> float:
        try:
            return float(fn())
        except ValueError:
            return float("nan")

    out["roc_auc"] = _maybe(lambda: roc_auc_score(y_t, s))
    out["pr_auc"] = _maybe(lambda: average_precision_score(y_t, s))

    cm = confusion_matrix(y_t, y_p, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel().tolist()
    out["confusion_matrix_tn"] = float(tn)
    out["confusion_matrix_fp"] = float(fp)
    out["confusion_matrix_fn"] = float(fn)
    out["confusion_matrix_tp"] = float(tp)
    return out
