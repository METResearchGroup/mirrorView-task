"""Analysis 1: surface metrics and classifiers on original text by cell.

Run from repo root::

    PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis1.py
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from experiments.unanimous_vs_majority_labels_2026_08_08.src.build_cohort import (
    COHORT_CSV,
)
from shared.textual_features import intergroup, prime, valence
from shared.textual_features.registry import (
    AVG_SENTENCE_LENGTH,
    CHAR_COUNT,
    FLESCH_KINCAID_GRADE,
    PUNCTUATION_DENSITY,
    READING_EASE,
    SENTENCE_COUNT,
    WORD_COUNT,
    get_feature,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS1_DIR = EXPERIMENT_ROOT / "outputs" / "analysis1"
PER_POST_CSV = ANALYSIS1_DIR / "per_post_features.csv"
CELL_SUMMARY_CSV = ANALYSIS1_DIR / "cell_summary.csv"

_CELL_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_METRIC_REGISTRY_NAMES = (
    CHAR_COUNT,
    WORD_COUNT,
    SENTENCE_COUNT,
    AVG_SENTENCE_LENGTH,
    PUNCTUATION_DENSITY,
    FLESCH_KINCAID_GRADE,
    READING_EASE,
)
_HIGH_TOXICITY = "sample_high_toxicity"
_CLASSIFIER_WORKERS = 32
_REQUIRED_COHORT_COLUMNS = ("message_id", "original_text", "cell", "sample_toxicity_type")


def _load_cohort(path: Path) -> pd.DataFrame:
    """Load the four-cell cohort and validate required columns.

    Parameters
    ----------
    path
        Path to ``four_cell_cohort.csv``.

    Returns
    -------
    pandas.DataFrame
        Cohort frame.

    Raises
    ------
    FileNotFoundError
        When the cohort file is missing.
    KeyError
        When required columns are absent.
    """
    if not path.is_file():
        raise FileNotFoundError(path.resolve())
    cohort = pd.read_csv(path)
    missing = [c for c in _REQUIRED_COHORT_COLUMNS if c not in cohort.columns]
    if missing:
        raise KeyError(f"Cohort missing required columns: {missing}")
    return cohort


def _compute_deterministic_metrics(texts: list[str]) -> pd.DataFrame:
    """Compute locked surface metrics for each original text.

    Parameters
    ----------
    texts
        Original post texts.

    Returns
    -------
    pandas.DataFrame
        One column per metric name returned by the registry.
    """
    metrics = []
    metric_names: list[str] = []
    for registry_name in _METRIC_REGISTRY_NAMES:
        entry = get_feature(registry_name)
        if entry.build is None:
            raise ValueError(f"Registry entry {registry_name} has no metric builder")
        metric = entry.build()
        metrics.append(metric)
        metric_names.append(metric.name)

    rows: list[dict[str, float]] = []
    for text in tqdm(texts, desc="Deterministic metrics"):
        row = {metric.name: float(metric.calculate(text)) for metric in metrics}
        rows.append(row)
    return pd.DataFrame(rows, columns=metric_names)


def _classify_column(
    texts: list[str],
    classify_fn,
    field_name: str,
    desc: str,
) -> list[bool]:
    """Classify each text with ``classify_fn`` and return boolean labels.

    Parameters
    ----------
    texts
        Original post texts.
    classify_fn
        Callable returning a structured label with ``field_name``.
    field_name
        Attribute to read from each classification result.
    desc
        Progress bar description.

    Returns
    -------
    list[bool]
        One label per input text, in input order.
    """
    labels: list[bool | None] = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=_CLASSIFIER_WORKERS) as executor:
        future_to_idx = {
            executor.submit(classify_fn, text): idx for idx, text in enumerate(texts)
        }
        for future in tqdm(as_completed(future_to_idx), total=len(texts), desc=desc):
            idx = future_to_idx[future]
            result = future.result()
            labels[idx] = bool(getattr(result, field_name))
    if any(label is None for label in labels):
        raise RuntimeError(f"Incomplete labels for {field_name}")
    return [bool(label) for label in labels]


def _build_per_post_features(cohort: pd.DataFrame) -> pd.DataFrame:
    """Attach deterministic metrics and classifiers to cohort rows.

    Parameters
    ----------
    cohort
        Four-cell cohort.

    Returns
    -------
    pandas.DataFrame
        Per-post feature table.
    """
    texts = cohort["original_text"].astype(str).tolist()
    metrics = _compute_deterministic_metrics(texts)
    is_positive = _classify_column(
        texts, valence.classify_post, "is_positive", "Valence"
    )
    is_intergroup = _classify_column(
        texts, intergroup.classify_post, "is_intergroup", "Intergroup"
    )
    is_prime = _classify_column(texts, prime.classify_post, "is_prime", "PRIME")

    out = cohort[["message_id", "cell", "sample_toxicity_type"]].copy()
    out = pd.concat([out.reset_index(drop=True), metrics.reset_index(drop=True)], axis=1)
    out["is_positive"] = is_positive
    out["is_intergroup"] = is_intergroup
    out["is_prime"] = is_prime
    return out


def _summarize_by_cell(per_post: pd.DataFrame) -> pd.DataFrame:
    """Build descriptive per-cell medians and classifier proportions.

    Parameters
    ----------
    per_post
        Per-post feature table.

    Returns
    -------
    pandas.DataFrame
        One row per cell in frozen order.
    """
    continuous_cols = [
        c
        for c in per_post.columns
        if c
        not in {
            "message_id",
            "cell",
            "sample_toxicity_type",
            "is_positive",
            "is_intergroup",
            "is_prime",
        }
    ]
    rows: list[dict[str, object]] = []
    for cell in _CELL_ORDER:
        subset = per_post[per_post["cell"] == cell]
        row: dict[str, object] = {
            "cell": cell,
            "n": int(len(subset)),
            "pct_high_toxicity": float(
                (subset["sample_toxicity_type"] == _HIGH_TOXICITY).mean()
            )
            if len(subset)
            else 0.0,
        }
        for col in continuous_cols:
            row[col] = float(subset[col].median()) if len(subset) else float("nan")
        for col in ("is_positive", "is_intergroup", "is_prime"):
            row[col] = float(subset[col].mean()) if len(subset) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def _print_char_medians(summary: pd.DataFrame) -> None:
    """Print character-count medians by cell for manual gradient checks."""
    if "char_count" not in summary.columns:
        return
    print("char_count medians by cell:")
    for _, row in summary.iterrows():
        print(f"  {row['cell']}: {row['char_count']}")


def run_analysis1(cohort_path: Path = COHORT_CSV) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run Analysis 1 and write per-post and cell-summary CSVs.

    Parameters
    ----------
    cohort_path
        Path to the four-cell cohort CSV.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Per-post features and cell summary.
    """
    cohort = _load_cohort(cohort_path)
    per_post = _build_per_post_features(cohort)
    summary = _summarize_by_cell(per_post)
    ANALYSIS1_DIR.mkdir(parents=True, exist_ok=True)
    per_post.to_csv(PER_POST_CSV, index=False)
    summary.to_csv(CELL_SUMMARY_CSV, index=False)
    return per_post, summary


def main() -> None:
    """CLI entry: run Analysis 1 and print a short summary."""
    per_post, summary = run_analysis1(COHORT_CSV)
    print(f"Wrote {PER_POST_CSV} rows={len(per_post)}")
    print(f"Wrote {CELL_SUMMARY_CSV} rows={len(summary)}")
    _print_char_medians(summary)
    print(summary[["cell", "n", "pct_high_toxicity"]].to_string(index=False))


if __name__ == "__main__":
    main()
