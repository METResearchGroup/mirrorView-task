"""Review table for named clusters."""

from __future__ import annotations

import pandas as pd


def empty_cluster_keys(rows: list[dict]) -> list[str]:
    """Return cluster keys whose name or definition is empty.

    Parameters
    ----------
    rows
        Naming rows with ``source_record_id``, ``name``, and ``definition``.

    Returns
    -------
    list[str]
        Cluster keys that still need a name or a definition.
    """
    empty: list[str] = []
    for row in rows:
        name = str(row.get("name", "")).strip()
        definition = str(row.get("definition", "")).strip()
        if not name or not definition:
            empty.append(str(row["source_record_id"]))
    return empty


def build_feature_review(
    rows: list[dict],
    sizes: pd.DataFrame,
    total_batches: int,
) -> pd.DataFrame:
    """Join names to cluster sizes for the review table.

    Parameters
    ----------
    rows
        Naming rows keyed by ``source_record_id``.
    sizes
        Step 4 size table.
    total_batches
        Mining batch count used as the share denominator.

    Returns
    -------
    pandas.DataFrame
        Columns ``cluster_key``, ``name``, ``definition``, ``n_features``,
        ``n_batches``, ``batch_share``, and ``kept_share``, sorted by
        ``n_batches`` descending and then ``cluster_key``.

    Raises
    ------
    ValueError
        When ``total_batches`` is not positive or a named cluster is missing.
    """
    if total_batches <= 0:
        raise ValueError(f"total_batches must be positive, got {total_batches}")
    by_key = {str(row["source_record_id"]): row for row in rows}
    records: list[dict[str, object]] = []
    for _, size_row in sizes.iterrows():
        cluster_key = str(size_row["cluster_key"])
        named = by_key.get(cluster_key)
        if named is None:
            raise ValueError(f"missing name for {cluster_key}")
        kept = int(size_row["n_kept_side"])
        removed = int(size_row["n_removed_side"])
        side_total = kept + removed
        kept_share = 0.0 if side_total == 0 else kept / side_total
        records.append(
            {
                "cluster_key": cluster_key,
                "name": named["name"],
                "definition": named["definition"],
                "n_features": int(size_row["n_features"]),
                "n_batches": int(size_row["n_batches"]),
                "batch_share": int(size_row["n_batches"]) / total_batches,
                "kept_share": kept_share,
            }
        )
    review = pd.DataFrame.from_records(records)
    return review.sort_values(
        ["n_batches", "cluster_key"],
        ascending=[False, True],
    ).reset_index(drop=True)


def render_review_markdown(review: pd.DataFrame) -> str:
    """Render the review table with shares as one-decimal percentages.

    Parameters
    ----------
    review
        Output of :func:`build_feature_review`.

    Returns
    -------
    str
        Markdown table.
    """
    lines = [
        "| Cluster | Name | Definition | Features | Batches | Batch share | Kept share |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in review.iterrows():
        lines.append(
            "| {cluster_key} | {name} | {definition} | {n_features} | {n_batches} | {batch_share} | {kept_share} |".format(
                cluster_key=row["cluster_key"],
                name=str(row["name"]).replace("|", "\\|"),
                definition=str(row["definition"]).replace("|", "\\|"),
                n_features=int(row["n_features"]),
                n_batches=int(row["n_batches"]),
                batch_share=f"{float(row['batch_share']) * 100:.1f}%",
                kept_share=f"{float(row['kept_share']) * 100:.1f}%",
            )
        )
    return "\n".join(lines)
