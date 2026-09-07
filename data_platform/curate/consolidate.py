from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from data_platform.utils.duckdb_features import feature_glob
from data_platform.utils.platform_specific_columns import STANDARDIZED_SOURCE_RECORD_ID_COLUMN

# Columns selected from each feature CSV (excluding the feature id column).
# Keys match FEATURE_REGISTRY. ``llm_toxicity_tiered`` is campaign-only; the
# default wide join still uses Perspective ``is_toxic_tiered``.
FEATURE_WIDE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "is_news_or_opinion": [("category", "news_or_opinion_category")],
    "is_political": [("is_political", "is_political")],
    "is_likely_spam": [("is_likely_spam", "is_likely_spam")],
    "is_self_contained": [("is_self_contained", "is_self_contained")],
    "is_structurally_complete": [("is_structurally_complete", "is_structurally_complete")],
    "is_toxic_tiered": [
        ("toxicity_prob", "toxicity_prob"),
        ("toxicity_tier", "toxicity_tier"),
    ],
    "political_stance": [("political_stance", "political_stance")],
    "llm_toxicity_tiered": [("toxicity_tier", "llm_toxicity_tier")],
}

DEFAULT_WIDE_FEATURE_NAMES: tuple[str, ...] = (
    "is_news_or_opinion",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "is_toxic_tiered",
    "political_stance",
)

LLM_CAMPAIGN_FEATURE_NAMES: tuple[str, ...] = (
    "is_news_or_opinion",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tiered",
)

PREPROCESSED_WIDE_COLUMNS: tuple[str, ...] = (
    "uri",
    "record_id",
    "url",
    "author_handle",
    "text",
    "created_at",
    "like_count",
    "repost_count",
    "reply_count",
    "quote_count",
    "sync_timestamp",
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
)

EXPECTED_WIDE_ROW_COUNT = 200000
WIDE_SORT_KEY = f"{STANDARDIZED_SOURCE_RECORD_ID_COLUMN} ASC"


@dataclass(frozen=True)
class ConsolidateConfig:
    """Join preprocessed records with deduped feature label CSVs.

    ``id_column`` is the join key on the preprocessed records CSV (e.g. ``uri`` for
    Bluesky, ``comment_fullname`` for Reddit). ``feature_file_id_column`` is the id
    column stored in feature CSV files (``source_record_id`` for every platform).
    """

    posts_file: Path
    features_root: Path
    feature_names: tuple[str, ...] = DEFAULT_WIDE_FEATURE_NAMES
    id_column: str = "uri"
    feature_file_id_column: str = STANDARDIZED_SOURCE_RECORD_ID_COLUMN


def _feature_cte_sql(
    feature_name: str,
    glob_pattern: str,
    *,
    id_column: str,
    feature_file_id_column: str,
    use_parquet: bool = False,
) -> str:
    column_pairs = FEATURE_WIDE_COLUMNS[feature_name]
    inner_cols = ", ".join(
        f"{source} AS {alias}" if source != alias else source for source, alias in column_pairs
    )
    outer_cols = ", ".join(alias for _, alias in column_pairs)
    cte_name = f"feat_{feature_name}"
    feature_id_expr = f"CAST({feature_file_id_column} AS VARCHAR) AS {id_column}"
    partition_id = f"CAST({feature_file_id_column} AS VARCHAR)"
    read_expr = (
        f"read_parquet('{glob_pattern}')"
        if use_parquet
        else f"read_csv('{glob_pattern}', union_by_name = true)"
    )
    return f"""
{cte_name} AS (
    SELECT {id_column}, {outer_cols}
    FROM (
        SELECT {feature_id_expr}, {inner_cols},
            ROW_NUMBER() OVER (
                PARTITION BY {partition_id}
                ORDER BY label_timestamp DESC NULLS LAST, {partition_id}
            ) AS rn
        FROM {read_expr}
    )
    WHERE rn = 1
)"""


def _build_consolidate_sql(config: ConsolidateConfig) -> str:
    id_column = config.id_column
    use_parquet = config.posts_file.suffix == ".parquet"
    feature_ext = ".parquet" if use_parquet else ".csv"
    posts_path = config.posts_file.as_posix()
    if use_parquet:
        posts_from = f"read_parquet('{posts_path}')"
    else:
        posts_from = f"read_csv('{posts_path}', union_by_name = true)"
    feature_ctes = [
        _feature_cte_sql(
            feature_name,
            feature_glob(config.features_root, feature_name, ext=feature_ext),
            id_column=id_column,
            feature_file_id_column=config.feature_file_id_column,
            use_parquet=use_parquet,
        )
        for feature_name in config.feature_names
        if feature_name in FEATURE_WIDE_COLUMNS
    ]
    join_clauses = [
        f"LEFT JOIN feat_{feature_name} USING ({id_column})"
        for feature_name in config.feature_names
        if feature_name in FEATURE_WIDE_COLUMNS
    ]
    wide_cols = []
    for feature_name in config.feature_names:
        if feature_name not in FEATURE_WIDE_COLUMNS:
            continue
        for _, alias in FEATURE_WIDE_COLUMNS[feature_name]:
            wide_cols.append(f"feat_{feature_name}.{alias}")

    ctes_sql = ",\n".join(
        [
            f"posts AS (SELECT * REPLACE (CAST({id_column} AS VARCHAR) AS {id_column}) "
            f"FROM {posts_from})"
        ]
        + feature_ctes
    )
    select_cols = ["posts.*"] + wide_cols
    return f"""
WITH {ctes_sql}
SELECT {", ".join(select_cols)}
FROM posts
{" ".join(join_clauses)}
"""


def build_wide_table(config: ConsolidateConfig) -> pd.DataFrame:
    """Join preprocessed records with deduped feature label CSVs on ``id_column``."""
    sql = _build_consolidate_sql(config)
    conn = duckdb.connect()
    try:
        return conn.execute(sql).fetchdf()
    finally:
        conn.close()


def llm_campaign_wide_columns() -> tuple[str, ...]:
    """Return the nineteen wide columns in campaign order."""
    label_columns = tuple(
        alias
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
        for _, alias in FEATURE_WIDE_COLUMNS[feature_name]
    )
    return PREPROCESSED_WIDE_COLUMNS + label_columns


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _campaign_posts_cte_sql(posts_file: Path) -> str:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    selected = ", ".join(
        f"CAST({column} AS VARCHAR) AS {column}" if column == id_column else column
        for column in PREPROCESSED_WIDE_COLUMNS
    )
    return f"posts AS (SELECT {selected} FROM read_parquet('{_sql_path(posts_file)}'))"


def _campaign_feature_ctes(feature_files: dict[str, Path]) -> list[str]:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    return [
        _feature_cte_sql(
            feature_name,
            _sql_path(feature_files[feature_name]),
            id_column=id_column,
            feature_file_id_column=id_column,
            use_parquet=True,
        )
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    ]


def _campaign_join_sql(posts_file: Path, feature_files: dict[str, Path]) -> str:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    join_clauses = [
        f"INNER JOIN feat_{feature_name} USING ({id_column})"
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    ]
    label_cols = [
        f"feat_{feature_name}.{alias}"
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
        for _, alias in FEATURE_WIDE_COLUMNS[feature_name]
    ]
    posts_cols = [f"posts.{column}" for column in PREPROCESSED_WIDE_COLUMNS]
    ctes = ",\n".join([_campaign_posts_cte_sql(posts_file), *_campaign_feature_ctes(feature_files)])
    return f"""
WITH {ctes}
SELECT {", ".join(posts_cols + label_cols)}
FROM posts
{" ".join(join_clauses)}
ORDER BY posts.{id_column} ASC
"""


def build_llm_campaign_wide_table(
    posts_file: Path,
    feature_files: dict[str, Path],
) -> pd.DataFrame:
    """Inner-join pinned posts to seven campaign ``final.parquet`` files on ``source_record_id``.

    Rows are sorted by ``source_record_id`` ascending. Duplicate feature ids keep
    the latest ``label_timestamp``.

    Raises
    ------
    KeyError
        When a campaign feature path is missing from ``feature_files``.
    """
    missing = [name for name in LLM_CAMPAIGN_FEATURE_NAMES if name not in feature_files]
    if missing:
        raise KeyError(f"missing campaign feature parquet paths: {missing}")
    sql = _campaign_join_sql(posts_file, feature_files)
    conn = duckdb.connect()
    try:
        return conn.execute(sql).fetchdf()
    finally:
        conn.close()
