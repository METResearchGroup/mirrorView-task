"""Count the most common features inside each pair group."""

from __future__ import annotations

import pandas as pd


def check_group_counts(groups: pd.Series, expected: dict) -> None:
    """Raise when any group's pair count differs from the pinned count.

    Parameters
    ----------
    groups
        One group label per pair, indexed by ``post_id``.
    expected
        Group label to the required pair count.
    """
    counts = groups.value_counts().to_dict()
    for label, expected_count in expected.items():
        actual = int(counts.get(label, 0))
        if actual != expected_count:
            raise ValueError(f"group {label} has {actual} pairs, expected {expected_count}")


def feature_proportions(
    labels: pd.DataFrame,
    groups: pd.Series,
    details: dict[str, dict[str, str]],
    group_order: list,
) -> pd.DataFrame:
    """Share of each group where each feature is present.

    Parameters
    ----------
    labels
        Label table with ``post_id`` and one 0 or 1 column per feature.
    groups
        Group label per pair, indexed by ``post_id``.
    details
        Feature key to ``name`` and ``description``.
    group_order
        Groups in x-axis order.

    Returns
    -------
    pandas.DataFrame
        One row per feature and group, with ``n_pairs``, ``n_group_pairs``,
        and ``proportion`` equal to ``n_pairs / n_group_pairs``.

    Raises
    ------
    ValueError
        When a grouped post has no label row.
    """
    label_index = labels.set_index("post_id")
    missing = groups.index.difference(label_index.index)
    if len(missing):
        raise ValueError(f"grouped post has no label row: {missing[0]}")
    records: list[dict[str, object]] = []
    for group in group_order:
        member_ids = groups.index[groups.astype(str) == str(group)]
        frame = label_index.loc[member_ids]
        n_group_pairs = len(frame)
        if n_group_pairs == 0:
            raise ValueError(f"group {group} has no pairs")
        for key, detail in details.items():
            n_pairs = int(frame[key].sum())
            records.append(
                {
                    "group": str(group),
                    "feature_key": key,
                    "name": detail["name"],
                    "n_pairs": n_pairs,
                    "n_group_pairs": n_group_pairs,
                    "proportion": n_pairs / n_group_pairs,
                }
            )
    return pd.DataFrame.from_records(records)


def top_features_by_group(
    labels: pd.DataFrame,
    groups: pd.Series,
    details: dict[str, dict[str, str]],
    top_n: int,
) -> pd.DataFrame:
    """Count feature presence inside each group and keep the top rows.

    Parameters
    ----------
    labels
        Label table with ``post_id`` and one 0 or 1 column per feature.
    groups
        Group label per pair, indexed by ``post_id``.
    details
        Feature key to ``name`` and ``description``.
    top_n
        How many features to keep in each group.

    Returns
    -------
    pandas.DataFrame
        Columns ``group``, ``n_group_pairs``, ``rank``, ``feature_key``,
        ``name``, and ``n_pairs``. Within a group, rows are ordered by
        ``n_pairs`` descending and then ``feature_key`` ascending.

    Raises
    ------
    ValueError
        When a grouped post has no label row.
    """
    label_index = labels.set_index("post_id")
    missing = groups.index.difference(label_index.index)
    if len(missing):
        raise ValueError(f"grouped post has no label row: {missing[0]}")
    feature_keys = list(details)
    joined = label_index.loc[groups.index, feature_keys].copy()
    joined["group"] = groups.to_numpy()
    records: list[dict[str, object]] = []
    for group, frame in joined.groupby("group", sort=False):
        n_group_pairs = len(frame)
        ranked = sorted(
            ((int(frame[key].sum()), key) for key in feature_keys),
            key=lambda item: (-item[0], item[1]),
        )
        for rank, (n_pairs, key) in enumerate(ranked[:top_n], start=1):
            records.append(
                {
                    "group": group,
                    "n_group_pairs": n_group_pairs,
                    "rank": rank,
                    "feature_key": key,
                    "name": details[key]["name"],
                    "n_pairs": n_pairs,
                }
            )
    return pd.DataFrame.from_records(records)
