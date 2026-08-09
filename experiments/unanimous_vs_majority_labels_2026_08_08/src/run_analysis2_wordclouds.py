"""Analysis 2 word clouds and top-token tables from merged Stage 1 features.

Run from repo root::

    PYTHONPATH=. uv run --with wordcloud python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd
from wordcloud import WordCloud

from experiments.unanimous_vs_majority_labels_2026_08_08.src.bow_tokens import (
    tokenize_feature_value,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS2_DIR = EXPERIMENT_ROOT / "outputs" / "analysis2"
MERGED_FEATURES_JSONL = ANALYSIS2_DIR / "merged_stage1_features.jsonl"
TOP_TOKENS_CSV = ANALYSIS2_DIR / "top_tokens_by_cell.csv"

_CELL_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_TOP_N = 30
_WORDCLOUD_WIDTH = 1200
_WORDCLOUD_HEIGHT = 800
_WORDCLOUD_BACKGROUND = "white"


def _load_merged_features(path: Path) -> pd.DataFrame:
    """Load merged Stage 1 feature rows from JSONL.

    Parameters
    ----------
    path
        Merged features JSONL path.

    Returns
    -------
    pandas.DataFrame
        Feature rows with message_id, feature_value, and cell.

    Raises
    ------
    FileNotFoundError
        When the merged features file is missing.
    ValueError
        When required columns are absent.
    """
    if not path.is_file():
        raise FileNotFoundError(path.resolve())
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    frame = pd.DataFrame(rows)
    required = {"message_id", "feature_value", "cell"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Merged features missing columns: {sorted(missing)}")
    return frame


def _token_counts_for_cell(frame: pd.DataFrame) -> Counter[str]:
    """Count posts containing each token inside one cell.

    Parameters
    ----------
    frame
        Feature rows for one cell.

    Returns
    -------
    collections.Counter
        Token to post-document-frequency counts.
    """
    tokens_by_post: dict[str, set[str]] = {}
    for _, row in frame.iterrows():
        message_id = str(row["message_id"])
        tokens = tokenize_feature_value(str(row["feature_value"]))
        if message_id not in tokens_by_post:
            tokens_by_post[message_id] = set()
        tokens_by_post[message_id] |= tokens

    counts: Counter[str] = Counter()
    for tokens in tokens_by_post.values():
        counts.update(tokens)
    return counts


def _top_token_rows(cell: str, counts: Counter[str], top_n: int) -> list[dict[str, object]]:
    """Build ranked top-token rows for one cell.

    Parameters
    ----------
    cell
        Four-cell label.
    counts
        Token document frequencies.
    top_n
        Maximum tokens to keep.

    Returns
    -------
    list[dict[str, object]]
        Rows with cell, token, n_posts, and rank.
    """
    ranked = counts.most_common(top_n)
    rows: list[dict[str, object]] = []
    for rank, (token, n_posts) in enumerate(ranked, start=1):
        rows.append(
            {
                "cell": cell,
                "token": token,
                "n_posts": int(n_posts),
                "rank": rank,
            }
        )
    return rows


def _write_wordcloud(counts: Counter[str], path: Path) -> None:
    """Write one word cloud PNG sized by post counts.

    Parameters
    ----------
    counts
        Token document frequencies.
    path
        Destination PNG path.
    """
    if not counts:
        # Still write an empty white image so the artifact path exists.
        cloud = WordCloud(
            width=_WORDCLOUD_WIDTH,
            height=_WORDCLOUD_HEIGHT,
            background_color=_WORDCLOUD_BACKGROUND,
        ).generate("empty")
    else:
        cloud = WordCloud(
            width=_WORDCLOUD_WIDTH,
            height=_WORDCLOUD_HEIGHT,
            background_color=_WORDCLOUD_BACKGROUND,
        ).generate_from_frequencies(counts)
    path.parent.mkdir(parents=True, exist_ok=True)
    cloud.to_file(str(path))


def run_analysis2_wordclouds(
    merged_path: Path = MERGED_FEATURES_JSONL,
    top_n: int = _TOP_N,
) -> pd.DataFrame:
    """Build top-token tables and four word-cloud PNGs.

    Parameters
    ----------
    merged_path
        Merged Stage 1 features JSONL.
    top_n
        Tokens per cell.

    Returns
    -------
    pandas.DataFrame
        Top tokens by cell.
    """
    features = _load_merged_features(merged_path)
    all_rows: list[dict[str, object]] = []
    for cell in _CELL_ORDER:
        subset = features[features["cell"] == cell]
        counts = _token_counts_for_cell(subset)
        all_rows.extend(_top_token_rows(cell, counts, top_n))
        png_path = ANALYSIS2_DIR / f"wordcloud_{cell}.png"
        _write_wordcloud(counts, png_path)
        print(f"Wrote {png_path} tokens={len(counts)}")
    tokens = pd.DataFrame(all_rows, columns=["cell", "token", "n_posts", "rank"])
    tokens.to_csv(TOP_TOKENS_CSV, index=False)
    print(f"Wrote {TOP_TOKENS_CSV} rows={len(tokens)}")
    return tokens


def main() -> None:
    """CLI entry: write top tokens and word clouds."""
    run_analysis2_wordclouds(MERGED_FEATURES_JSONL, _TOP_N)


if __name__ == "__main__":
    main()
