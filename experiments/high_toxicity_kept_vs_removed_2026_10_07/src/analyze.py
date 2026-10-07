"""Break high-toxicity Study 2 posts into modal keep and modal remove.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/high_toxicity_kept_vs_removed_2026_10_07/src/analyze.py
"""

from __future__ import annotations

import os
import textwrap
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.label_to_detail import (
    LABEL_TO_DETAIL,
)
from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from lib.constants import REPO_ROOT
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_2_KEEP_REMOVE_LABELS

EXPERIMENT_NAME = "high_toxicity_kept_vs_removed_2026_10_07"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_NAME
OUTPUT_DIR = EXPERIMENT_DIR / "outputs"
CACHE_DIR = OUTPUT_DIR / "cache"
BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = f"experiments/{EXPERIMENT_NAME}"

ASSIGNMENTS_KEY = (
    "experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/topics/original/"
    "20260924T135151Z/assignments.parquet"
)
TOPIC_LABELS_KEY = (
    "experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/labels/original/"
    "20260924T135628Z/topic_labels.parquet"
)
FACET_KEY = (
    "experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/analyses/outcomes/"
    "20260924T140052Z/outcomes_by_topic_facet.csv"
)
FEATURES_KEY = (
    "experiments/study_2_llm_based_feature_extraction_2026_09_29/"
    "step6_label_posts_with_features/post_feature_labels.parquet"
)

HIGH_TOXICITY = "sample_high_toxicity"
KEEP = "keep"
REMOVE = "remove"
MIN_RATERS = 3
MIN_TOPIC_POSTS = 30
EXPECTED_POSTS = 4983
EXPECTED_UNGROUPED = 2091
EXPECTED_KEEP_RATE_PERCENT = 49.8
NOISE_TOPIC_ID = -1
OTHER_TOPIC_ID = -2
UNGROUPED_NAME = "Ungrouped"
OTHER_NAME = "Other grouped topics"
EXCERPT_CHARS = 280
EXCERPTS_PER_SIDE = 2
EXCERPT_GROUPS = 3
KEEP_COLOR = "#0072B2"
REMOVE_COLOR = "#D55E00"

TOPIC_COLUMNS = [
    "topic_id",
    "topic_name",
    "n_posts",
    "n_modal_keep",
    "n_modal_remove",
    "share_of_modal_keep",
    "share_of_modal_remove",
    "mean_keep_rate",
]
FEATURE_COLUMNS = [
    "feature_key",
    "name",
    "n_present",
    "presence_rate_modal_keep",
    "presence_rate_modal_remove",
    "presence_gap",
    "mean_keep_rate_present",
    "mean_keep_rate_absent",
]


def display_label(raw: object) -> str:
    """Return the topic name before a parenthetical note.

    This is the same rule as ``display_label`` in
    ``experiments/bertopic_original_mirror_study_2_2026_09_24/src/export_map_data.py``.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return ""
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.split(" (", 1)[0].strip()


def _use_lab_credentials() -> None:
    """Copy lab AWS keys into the standard env vars when those are empty."""
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        access_key = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = access_key
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        secret_key = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key


def _cached_bytes(store: S3, key: str, filename: str) -> bytes:
    """Download ``key`` once and reuse the local cache."""
    path = CACHE_DIR / filename
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(store.get_bytes(key))
    return path.read_bytes()


def _read_parquet(store: S3, key: str, filename: str) -> pd.DataFrame:
    """Load a cached parquet object."""
    return pd.read_parquet(BytesIO(_cached_bytes(store, key, filename)))


def _read_csv(store: S3, key: str, filename: str) -> pd.DataFrame:
    """Load a cached CSV object."""
    return pd.read_csv(BytesIO(_cached_bytes(store, key, filename)))


def _require_columns(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    """Raise when ``source`` is missing a column."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"{source} missing columns: {missing}")


def load_high_toxicity_posts(store: S3) -> pd.DataFrame:
    """Join labels, original-post topics, and feature labels.

    Returns
    -------
    pandas.DataFrame
        One row per high-toxicity post in the original-post topic fit.

    Raises
    ------
    ValueError
        When the row count, keep rate, or feature coverage disagrees with the
        published Study 2 figures.
    """
    labels = load_dataset(STUDY_2_KEEP_REMOVE_LABELS, low_memory=False)
    _require_columns(
        labels,
        ["post_id", "decision", "keep_rate", "n_raters", "sample_toxicity_type", "original_text"],
        "keep/remove labels",
    )
    labels = labels.copy()
    labels["post_id"] = labels["post_id"].astype(str).str.strip()
    labels["decision"] = labels["decision"].astype(str).str.strip()
    rated = labels.loc[
        (labels["n_raters"] >= MIN_RATERS) & labels["decision"].isin([KEEP, REMOVE])
    ].copy()

    assignments = _read_parquet(store, ASSIGNMENTS_KEY, "assignments.parquet")
    _require_columns(assignments, ["post_id", "topic", "text_role"], "assignments")
    original = assignments.loc[assignments["text_role"].astype(str) == "original", ["post_id", "topic"]]
    original = original.copy()
    original["post_id"] = original["post_id"].astype(str).str.strip()
    original["topic_id"] = original["topic"].astype(int)
    if original["post_id"].duplicated().any():
        raise ValueError("original-post assignments have a duplicate post_id")

    topic_labels = _read_parquet(store, TOPIC_LABELS_KEY, "topic_labels.parquet")
    _require_columns(topic_labels, ["topic_id", "llm_label"], "topic labels")
    names = {
        int(row.topic_id): display_label(row.llm_label)
        for row in topic_labels.itertuples(index=False)
    }
    names[NOISE_TOPIC_ID] = UNGROUPED_NAME

    features = _read_parquet(store, FEATURES_KEY, "post_feature_labels.parquet")
    feature_keys = list(LABEL_TO_DETAIL)
    _require_columns(features, ["post_id", *feature_keys], "feature labels")
    features = features.copy()
    features["post_id"] = features["post_id"].astype(str).str.strip()
    if features["post_id"].duplicated().any():
        raise ValueError("feature labels have a duplicate post_id")
    for key in feature_keys:
        features[key] = features[key].astype(int)

    joined = rated.merge(original[["post_id", "topic_id"]], on="post_id", how="inner")
    high = joined.loc[joined["sample_toxicity_type"].astype(str) == HIGH_TOXICITY].copy()
    if len(high) != EXPECTED_POSTS:
        raise ValueError(f"expected {EXPECTED_POSTS} high-toxicity posts, found {len(high)}")
    labeled = high.merge(features[["post_id", *feature_keys]], on="post_id", how="left")
    missing_features = int(labeled[feature_keys[0]].isna().sum())
    if missing_features:
        raise ValueError(f"{missing_features} high-toxicity posts have no feature row")
    missing_names = sorted(set(labeled["topic_id"].astype(int)) - set(names))
    if missing_names:
        raise ValueError(f"topics with no stored name: {missing_names}")
    labeled["topic_name"] = labeled["topic_id"].map(names)
    blank_names = labeled["topic_name"].astype(str).str.strip().eq("")
    if blank_names.any():
        topic_id = int(labeled.loc[blank_names, "topic_id"].iloc[0])
        raise ValueError(f"topic {topic_id} has an empty name")

    mean_keep_rate = float(labeled["keep_rate"].mean())
    rounded = round(100 * mean_keep_rate, 1)
    if rounded != EXPECTED_KEEP_RATE_PERCENT:
        raise ValueError(
            f"mean keep rate rounds to {rounded}, expected {EXPECTED_KEEP_RATE_PERCENT}"
        )
    ungrouped = int((labeled["topic_id"] == NOISE_TOPIC_ID).sum())
    if ungrouped != EXPECTED_UNGROUPED:
        raise ValueError(f"expected {EXPECTED_UNGROUPED} ungrouped posts, found {ungrouped}")
    return labeled.reset_index(drop=True)


def _group_summary(part: pd.DataFrame, topic_id: int, topic_name: str) -> dict[str, object]:
    """Count one topic group."""
    decisions = part["decision"].astype(str)
    return {
        "topic_id": topic_id,
        "topic_name": topic_name,
        "n_posts": int(len(part)),
        "n_modal_keep": int((decisions == KEEP).sum()),
        "n_modal_remove": int((decisions == REMOVE).sum()),
        "mean_keep_rate": float(part["keep_rate"].mean()) if len(part) else np.nan,
    }


def topic_table(posts: pd.DataFrame) -> pd.DataFrame:
    """One row per large topic, plus ungrouped and the small-topic rollup.

    Shares use the modal counts of the full high-toxicity set, so the rows
    sum to every post.
    """
    rows: list[dict[str, object]] = []
    small_parts: list[pd.DataFrame] = []
    for topic_id, part in posts.groupby("topic_id", sort=False):
        topic_int = int(topic_id)
        if topic_int == NOISE_TOPIC_ID:
            rows.append(_group_summary(part, topic_int, UNGROUPED_NAME))
            continue
        if len(part) >= MIN_TOPIC_POSTS:
            name = str(part["topic_name"].iloc[0])
            rows.append(_group_summary(part, topic_int, name))
            continue
        small_parts.append(part)
    if small_parts:
        other = pd.concat(small_parts, ignore_index=True)
    else:
        other = posts.iloc[0:0]
    rows.append(_group_summary(other, OTHER_TOPIC_ID, OTHER_NAME))

    table = pd.DataFrame(rows)
    n_keep = int((posts["decision"] == KEEP).sum())
    n_remove = int((posts["decision"] == REMOVE).sum())
    if n_keep == 0 or n_remove == 0:
        raise ValueError("one modal group is empty")
    table["share_of_modal_keep"] = table["n_modal_keep"] / n_keep
    table["share_of_modal_remove"] = table["n_modal_remove"] / n_remove
    if int(table["n_posts"].sum()) != len(posts):
        raise ValueError("topic rows do not sum to the high-toxicity posts")
    named = table.loc[~table["topic_id"].isin([NOISE_TOPIC_ID, OTHER_TOPIC_ID])].sort_values(
        ["mean_keep_rate", "topic_name"], ascending=[True, True]
    )
    tail = table.loc[table["topic_id"].isin([OTHER_TOPIC_ID, NOISE_TOPIC_ID])]
    ordered = pd.concat([named, tail], ignore_index=True)
    return ordered[TOPIC_COLUMNS]


def check_against_facet_table(posts: pd.DataFrame, store: S3) -> None:
    """Require large-topic counts to match the published topic-by-toxicity file."""
    facet = _read_csv(store, FACET_KEY, "outcomes_by_topic_facet.csv")
    _require_columns(facet, ["facet", "facet_value", "topic", "n_posts", "keep_rate"], "facet outcomes")
    high = facet.loc[
        (facet["facet"].astype(str) == "sample_toxicity_type")
        & (facet["facet_value"].astype(str) == HIGH_TOXICITY)
    ].copy()
    high["topic_id"] = high["topic"].astype(int)
    ours = (
        posts.groupby("topic_id")
        .agg(n_posts=("post_id", "size"), mean_keep_rate=("keep_rate", "mean"))
        .reset_index()
    )
    ours = ours.loc[ours["n_posts"] >= MIN_TOPIC_POSTS]
    published_ids = set(high["topic_id"].astype(int))
    our_ids = set(ours["topic_id"].astype(int))
    if published_ids != our_ids:
        raise ValueError(
            "high-toxicity topics with at least 30 posts differ from "
            f"outcomes_by_topic_facet.csv: extra={sorted(our_ids - published_ids)} "
            f"missing={sorted(published_ids - our_ids)}"
        )
    merged = ours.merge(high[["topic_id", "n_posts", "keep_rate"]], on="topic_id", suffixes=("_ours", "_published"))
    for row in merged.itertuples(index=False):
        if int(row.n_posts_ours) != int(row.n_posts_published):
            raise ValueError(
                f"topic {int(row.topic_id)} has {int(row.n_posts_ours)} posts, "
                f"published file has {int(row.n_posts_published)}"
            )
        if not np.isclose(float(row.mean_keep_rate), float(row.keep_rate), rtol=0, atol=1e-9):
            raise ValueError(
                f"topic {int(row.topic_id)} keep rate {float(row.mean_keep_rate)} "
                f"disagrees with published {float(row.keep_rate)}"
            )


def feature_table(posts: pd.DataFrame) -> pd.DataFrame:
    """Presence and keep rate for each stored feature, sorted by absolute gap."""
    keep = posts.loc[posts["decision"] == KEEP]
    remove = posts.loc[posts["decision"] == REMOVE]
    rows: list[dict[str, object]] = []
    for key, detail in LABEL_TO_DETAIL.items():
        present = posts[key].astype(int) == 1
        present_keep = keep[key].astype(int) == 1
        present_remove = remove[key].astype(int) == 1
        rate_keep = float(present_keep.mean())
        rate_remove = float(present_remove.mean())
        rows.append(
            {
                "feature_key": key,
                "name": detail["name"],
                "n_present": int(present.sum()),
                "presence_rate_modal_keep": rate_keep,
                "presence_rate_modal_remove": rate_remove,
                "presence_gap": rate_keep - rate_remove,
                "mean_keep_rate_present": float(posts.loc[present, "keep_rate"].mean()) if present.any() else np.nan,
                "mean_keep_rate_absent": float(posts.loc[~present, "keep_rate"].mean()) if (~present).any() else np.nan,
            }
        )
    table = pd.DataFrame(rows)
    if len(table) != len(LABEL_TO_DETAIL):
        raise ValueError("feature table is missing a label")
    table["abs_gap"] = table["presence_gap"].abs()
    table = table.sort_values(["abs_gap", "feature_key"], ascending=[False, True]).drop(columns=["abs_gap"])
    return table[FEATURE_COLUMNS].reset_index(drop=True)


def _truncate(text: object) -> str:
    """Collapse whitespace and cut the text at 280 characters."""
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= EXCERPT_CHARS:
        return collapsed
    return collapsed[: EXCERPT_CHARS - 3].rstrip() + "..."


def _pick_side(part: pd.DataFrame, decision: str) -> list[str]:
    """Return two excerpts from one modal group, ordered by keep rate.

    Posts shorter than 80 characters are skipped when the group still has two
    longer posts, so a one-line reply does not stand in for the topic.
    """
    side = part.loc[part["decision"] == decision].copy()
    if len(side) < EXCERPTS_PER_SIDE:
        raise ValueError(f"need {EXCERPTS_PER_SIDE} {decision} excerpts, found {len(side)}")
    side["excerpt"] = side["original_text"].map(_truncate)
    long_enough = side.loc[side["excerpt"].str.len() >= 80]
    pool = long_enough if len(long_enough) >= EXCERPTS_PER_SIDE else side
    ascending = decision == REMOVE
    ordered = pool.sort_values(["keep_rate", "post_id"], ascending=[ascending, True])
    return ordered["excerpt"].head(EXCERPTS_PER_SIDE).tolist()


def topic_excerpts(posts: pd.DataFrame, topics: pd.DataFrame) -> list[dict[str, object]]:
    """Excerpts for the three topics whose keep and remove shares differ most."""
    named = topics.loc[~topics["topic_id"].isin([NOISE_TOPIC_ID, OTHER_TOPIC_ID])].copy()
    named["share_gap"] = (named["share_of_modal_keep"] - named["share_of_modal_remove"]).abs()
    chosen = named.sort_values(["share_gap", "topic_name"], ascending=[False, True]).head(EXCERPT_GROUPS)
    excerpts: list[dict[str, object]] = []
    for row in chosen.itertuples(index=False):
        part = posts.loc[posts["topic_id"] == int(row.topic_id)]
        excerpts.append(
            {
                "kind": "topic",
                "name": row.topic_name,
                "keep": _pick_side(part, KEEP),
                "remove": _pick_side(part, REMOVE),
            }
        )
    return excerpts


def feature_excerpts(posts: pd.DataFrame, features: pd.DataFrame) -> list[dict[str, object]]:
    """Excerpts for the three features with the largest presence gap."""
    chosen = features.head(EXCERPT_GROUPS)
    excerpts: list[dict[str, object]] = []
    for row in chosen.itertuples(index=False):
        part = posts.loc[posts[row.feature_key].astype(int) == 1]
        excerpts.append(
            {
                "kind": "feature",
                "name": row.name,
                "keep": _pick_side(part, KEEP),
                "remove": _pick_side(part, REMOVE),
            }
        )
    return excerpts


def _percent(value: float) -> str:
    """Format a proportion as a percent with one decimal."""
    return f"{100 * value:.1f}%"


def _points(value: float) -> str:
    """Format a proportion difference as signed percentage points."""
    points = 100 * value
    return f"{points:+.1f} points"


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a markdown table."""
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def render_results(
    posts: pd.DataFrame,
    topics: pd.DataFrame,
    features: pd.DataFrame,
    excerpts: list[dict[str, object]],
) -> str:
    """Build RESULTS.md from the two tables and the excerpts."""
    n_keep = int((posts["decision"] == KEEP).sum())
    n_remove = int((posts["decision"] == REMOVE).sum())
    mean_keep_rate = float(posts["keep_rate"].mean())
    topic_rows = [
        [
            str(row.topic_name),
            f"{int(row.n_posts):,}",
            f"{int(row.n_modal_keep):,}",
            f"{int(row.n_modal_remove):,}",
            _percent(float(row.share_of_modal_keep)),
            _percent(float(row.share_of_modal_remove)),
            _percent(float(row.mean_keep_rate)),
        ]
        for row in topics.itertuples(index=False)
    ]
    feature_rows = [
        [
            str(row.name),
            f"{int(row.n_present):,}",
            _percent(float(row.presence_rate_modal_keep)),
            _percent(float(row.presence_rate_modal_remove)),
            _points(float(row.presence_gap)),
            _percent(float(row.mean_keep_rate_present)),
            _percent(float(row.mean_keep_rate_absent)),
        ]
        for row in features.itertuples(index=False)
    ]
    excerpt_blocks: list[str] = []
    for item in excerpts:
        kept = "\n\n".join(f"> {text}" for text in item["keep"])
        removed = "\n\n".join(f"> {text}" for text in item["remove"])
        excerpt_blocks.append(
            f"### {item['name']}\n\nModal keep:\n\n{kept}\n\nModal remove:\n\n{removed}"
        )
    topic_md = _markdown_table(
        ["Topic", "Posts", "Modal keep", "Modal remove", "Share of kept", "Share of removed", "Keep rate"],
        topic_rows,
    )
    feature_md = _markdown_table(
        ["Feature", "Posts with feature", "Share of kept", "Share of removed", "Gap", "Keep rate if present", "Keep rate if absent"],
        feature_rows,
    )
    lines = [
        "# Which high-toxicity posts are kept",
        "",
        (
            f"The population is the {EXPECTED_POSTS:,} high-toxicity posts in the topic fit "
            f"on the original posts. The mean keep rate is {_percent(mean_keep_rate)}. "
            "That is the average of each post's own keep rate. "
            f"The stored modal label splits the same posts into {n_keep:,} keep and {n_remove:,} remove. "
            "A tie is remove."
        ),
        "",
        (
            f"Topics with at least {MIN_TOPIC_POSTS} high-toxicity posts are listed on their own. "
            "Smaller grouped topics are one row. Ungrouped posts are their own row. "
            f"For every topic with at least {MIN_TOPIC_POSTS} posts, the post count and the mean "
            "keep rate match `outcomes_by_topic_facet.csv`."
        ),
        "",
        (
            "A feature count uses the stored 0 or 1 label. The gap is the share of modal keep "
            "posts with the feature, minus the share of modal remove posts with the feature. "
            "Positive means the feature is more common among kept posts."
        ),
        "",
        "## Topics",
        "",
        topic_md,
        "",
        "## Features",
        "",
        feature_md,
        "",
        "## Excerpts",
        "",
        (
            "Excerpts are the original post text. For a topic, they are posts in that topic. "
            "For a feature, they are posts where the feature is present. Within a side, the two "
            "keep excerpts are the highest keep rates among posts of at least 80 characters, and "
            "the two remove excerpts are the lowest keep rates among those posts. "
            f"Each excerpt is at most {EXCERPT_CHARS} characters."
        ),
        "",
        "\n\n".join(excerpt_blocks),
        "",
        "## Files",
        "",
        "| Item | Path |",
        "| --- | --- |",
        "| Topic table | `outputs/tables/topics.csv` |",
        "| Feature table | `outputs/tables/features.csv` |",
        "| Topic figure | `outputs/figures/topic_composition.png` |",
        "| Feature figure | `outputs/figures/feature_presence_gap.png` |",
        "",
        f"`s3://{BUCKET}/{S3_PREFIX}/`",
        "",
    ]
    return "\n".join(lines)


def plot_topic_composition(topics: pd.DataFrame, path: Path) -> None:
    """Horizontal bars of each named topic's share of the two modal groups.

    Ungrouped posts and the small-topic rollup are left off the chart. Each is
    about the same share of both modal groups, and plotting them on this axis
    hides the named topics.
    """
    plot = topics.loc[~topics["topic_id"].isin([NOISE_TOPIC_ID, OTHER_TOPIC_ID])].copy()
    plot["share_gap"] = plot["share_of_modal_remove"] - plot["share_of_modal_keep"]
    plot = plot.sort_values("share_gap", ascending=True)
    labels = [textwrap.fill(str(name), width=42) for name in plot["topic_name"]]
    y = np.arange(len(plot))
    height = 0.38
    figure, axis = plt.subplots(figsize=(11, max(6, 0.48 * len(plot) + 1.4)))
    axis.barh(y - height / 2, 100 * plot["share_of_modal_keep"], height=height, color=KEEP_COLOR, label="Share of majority keep")
    axis.barh(y + height / 2, 100 * plot["share_of_modal_remove"], height=height, color=REMOVE_COLOR, label="Share of majority remove")
    axis.set_yticks(y, labels)
    axis.set_xlabel("Share of that group (%)")
    axis.set_title("Named topics among high-toxicity posts")
    axis.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.62, 1.06))
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def plot_feature_gaps(features: pd.DataFrame, path: Path) -> None:
    """Horizontal bars of the presence gap for every feature."""
    plot = features.sort_values("presence_gap", ascending=True)
    labels = [textwrap.fill(str(name), width=42) for name in plot["name"]]
    values = 100 * plot["presence_gap"].to_numpy(dtype=float)
    colors = [KEEP_COLOR if value >= 0 else REMOVE_COLOR for value in values]
    figure, axis = plt.subplots(figsize=(10, max(6, 0.32 * len(plot) + 1.2)))
    axis.barh(np.arange(len(plot)), values, color=colors)
    axis.set_yticks(np.arange(len(plot)), labels)
    axis.axvline(0, color="#444444", linewidth=0.8)
    axis.set_xlabel("Presence in majority keep minus presence in majority remove (points)")
    axis.set_title("Feature gap inside high-toxicity posts")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def _upload(store: S3, path: Path, relative: str) -> None:
    """Upload one output file."""
    content_type = "text/csv" if path.suffix == ".csv" else "image/png"
    store.upload_file(path, f"{S3_PREFIX}/{relative}", content_type=content_type)


def main() -> None:
    """Join the stored files, write the tables, and upload them."""
    _use_lab_credentials()
    store = S3(BUCKET, region_name=DEFAULT_REGION_NAME)
    posts = load_high_toxicity_posts(store)
    check_against_facet_table(posts, store)
    topics = topic_table(posts)
    features = feature_table(posts)
    excerpts = topic_excerpts(posts, topics) + feature_excerpts(posts, features)

    table_dir = OUTPUT_DIR / "tables"
    figure_dir = OUTPUT_DIR / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    topics_path = table_dir / "topics.csv"
    features_path = table_dir / "features.csv"
    topic_figure = figure_dir / "topic_composition.png"
    feature_figure = figure_dir / "feature_presence_gap.png"
    topics.to_csv(topics_path, index=False)
    features.to_csv(features_path, index=False)
    plot_topic_composition(topics, topic_figure)
    plot_feature_gaps(features, feature_figure)
    results = render_results(posts, topics, features, excerpts)
    (EXPERIMENT_DIR / "RESULTS.md").write_text(results, encoding="utf-8")
    _upload(store, topics_path, "tables/topics.csv")
    _upload(store, features_path, "tables/features.csv")
    _upload(store, topic_figure, "figures/topic_composition.png")
    _upload(store, feature_figure, "figures/feature_presence_gap.png")
    n_keep = int((posts["decision"] == KEEP).sum())
    n_remove = int((posts["decision"] == REMOVE).sum())
    print(f"posts={len(posts)} modal_keep={n_keep} modal_remove={n_remove} topics={len(topics)} features={len(features)}")


if __name__ == "__main__":
    main()
