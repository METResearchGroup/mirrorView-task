"""Build the joint-fit map files and upload them to S3.

The files are not written into the repo. The public page reads them from S3.

Run from repo root::

    PYTHONPATH=. uv run python \\
      experiments/bertopic_original_mirror_study_2_2026_09_24/src/export_map_data.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

BUCKET = "mirrorview-experimental-artifacts"
PREFIX = "experiments/bertopic_original_mirror_study_2_2026_09_24"
TOPICS_RUN = "20260924T135414Z"
LABELS_RUN = "20260924T135924Z"
POINTS_KEY = f"{PREFIX}/outputs/map/map-points.json"
TEXTS_KEY = f"{PREFIX}/outputs/map/map-texts.json"
LABELS_CSV_KEY = "shared/data/transformed/study_2/keep_remove_labels.csv"
UNGROUPED = "Ungrouped"
LEFT = "left"
RIGHT = "right"


def _client():
    """Return an S3 client using the lab credentials."""
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"),
    )


def _download(client, key: str, dest: Path) -> None:
    """Download one S3 object when it is not already on disk."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    client.download_file(BUCKET, key, str(dest))


def display_label(raw: object) -> str:
    """Return a short topic name from the stored label.

    Parameters
    ----------
    raw
        Label cell. Empty values become an empty string.

    Returns
    -------
    str
        Text before a parenthetical note, stripped.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return ""
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.split(" (", 1)[0].strip()


def build_payloads(work: Path) -> tuple[dict, list[str]]:
    """Join coordinates, labels, text, and stance into the two payloads.

    Parameters
    ----------
    work
        Directory that holds the downloaded inputs.

    Returns
    -------
    tuple[dict, list[str]]
        Point payload, and texts aligned to the same row order.
    """
    assignments = pd.read_parquet(work / "assignments.parquet")
    coordinates = np.load(work / "umap_2d.npy")
    if coordinates.shape != (len(assignments), 2):
        raise ValueError(f"umap_2d shape {coordinates.shape} != {len(assignments)} rows")
    topic_labels = pd.read_parquet(work / "topic_labels.parquet")
    posts = pd.read_csv(
        work / "keep_remove_labels.csv",
        usecols=["post_id", "original_text", "mirror_text", "sampled_stance"],
        low_memory=False,
    )
    posts["post_id"] = posts["post_id"].astype(str).str.strip()
    posts = posts.drop_duplicates("post_id", keep="first")
    by_id = posts.set_index("post_id")

    label_by_topic = {UNGROUPED_ID: UNGROUPED}
    for row in topic_labels.itertuples(index=False):
        topic_id = int(row.topic_id)
        if topic_id < 0:
            label_by_topic[topic_id] = UNGROUPED
            continue
        name = display_label(row.llm_label) or display_label(row.ctfidf_name) or f"Topic {topic_id}"
        label_by_topic[topic_id] = name

    original_at: dict[str, int] = {}
    mirror_at: dict[str, int] = {}
    for index, row in enumerate(assignments.itertuples(index=False)):
        post_id = str(row.post_id)
        if row.text_role == "original":
            original_at[post_id] = index
        elif row.text_role == "mirror":
            mirror_at[post_id] = index
        else:
            raise ValueError(f"Unexpected text role {row.text_role!r}")
    missing_pairs = set(original_at) ^ set(mirror_at)
    if missing_pairs:
        raise ValueError(f"{len(missing_pairs)} posts are missing an original or a mirror")

    roles: list[int] = []
    leans: list[int] = []
    topics: list[int] = []
    pairs: list[int] = []
    texts: list[str] = []
    missing_posts = 0
    unknown_stance = 0
    for index, row in enumerate(assignments.itertuples(index=False)):
        post_id = str(row.post_id)
        is_mirror = row.text_role == "mirror"
        pairs.append(mirror_at[post_id] if not is_mirror else original_at[post_id])
        roles.append(1 if is_mirror else 0)
        topics.append(int(row.topic))
        if post_id not in by_id.index:
            missing_posts += 1
            leans.append(2)
            texts.append("")
            continue
        record = by_id.loc[post_id]
        stance = str(record.sampled_stance).strip().lower()
        if stance not in {LEFT, RIGHT}:
            unknown_stance += 1
            leans.append(2)
        else:
            if is_mirror:
                stance = RIGHT if stance == LEFT else LEFT
            leans.append(0 if stance == LEFT else 1)
        text_column = "mirror_text" if is_mirror else "original_text"
        text = record[text_column]
        texts.append("" if pd.isna(text) else str(text))

    if missing_posts:
        raise ValueError(f"{missing_posts} map rows have no stimulus record")
    if unknown_stance:
        raise ValueError(f"{unknown_stance} map rows have an unknown stance")

    points = {
        "labels": {str(topic_id): name for topic_id, name in sorted(label_by_topic.items())},
        "x": [round(float(value), 4) for value in coordinates[:, 0]],
        "y": [round(float(value), 4) for value in coordinates[:, 1]],
        "role": roles,
        "lean": leans,
        "topic": topics,
        "pair": pairs,
    }
    return points, texts


UNGROUPED_ID = -1


def main() -> None:
    """Download the joint fit, write the two JSON objects, and upload them."""
    client = _client()
    work = Path("/tmp/joint-map")
    _download(client, f"{PREFIX}/outputs/topics/joint/{TOPICS_RUN}/assignments.parquet", work / "assignments.parquet")
    _download(client, f"{PREFIX}/outputs/topics/joint/{TOPICS_RUN}/umap_2d.npy", work / "umap_2d.npy")
    _download(
        client,
        f"{PREFIX}/outputs/labels/joint/{LABELS_RUN}/topic_labels.parquet",
        work / "topic_labels.parquet",
    )
    _download(client, LABELS_CSV_KEY, work / "keep_remove_labels.csv")
    points, texts = build_payloads(work)
    points_path = work / "map-points.json"
    texts_path = work / "map-texts.json"
    points_path.write_text(json.dumps(points, separators=(",", ":")), encoding="utf-8")
    texts_path.write_text(json.dumps(texts, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    client.upload_file(
        str(points_path),
        BUCKET,
        POINTS_KEY,
        ExtraArgs={"ContentType": "application/json"},
    )
    client.upload_file(
        str(texts_path),
        BUCKET,
        TEXTS_KEY,
        ExtraArgs={"ContentType": "application/json"},
    )
    print(f"points_bytes={points_path.stat().st_size}")
    print(f"texts_bytes={texts_path.stat().st_size}")
    print(f"n={len(texts)}")
    print(f"s3://{BUCKET}/{POINTS_KEY}")
    print(f"s3://{BUCKET}/{TEXTS_KEY}")


if __name__ == "__main__":
    main()
