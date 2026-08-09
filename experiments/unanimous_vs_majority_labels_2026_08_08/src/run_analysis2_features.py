"""Analysis 2 Stage 1 features: reuse prior rows and generate missing posts.

Run from repo root::

    PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from experiments.create_llm_features_2026_08_05.src.llm_generate_features import (
    DEFAULT_MODEL,
    DEFAULT_POSTS_PER_BATCH,
    prompt_fn,
    writer_map_fn,
)
from experiments.create_llm_features_2026_08_05.src.paths import LabelClass
from experiments.create_llm_features_2026_08_05.src.schemas import (
    SingleClassBatchFeatureGeneration,
)
from experiments.unanimous_vs_majority_labels_2026_08_08.src.build_cohort import (
    COHORT_CSV,
)
from research_tools.llm_service import LLMService

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS2_DIR = EXPERIMENT_ROOT / "outputs" / "analysis2"
MERGED_FEATURES_JSONL = ANALYSIS2_DIR / "merged_stage1_features.jsonl"
COVERAGE_JSON = ANALYSIS2_DIR / "coverage.json"
GENERATED_ROOT = ANALYSIS2_DIR / "generated_features"
PRIOR_FEATURES_ROOT = Path(
    "experiments/create_llm_features_2026_08_05/outputs/generated_features"
)

_KEEP_CELLS = frozenset({"unanimous_keep", "majority_keep"})
_REMOVE_CELLS = frozenset({"unanimous_remove", "majority_remove"})
_FEATURE_FIELDS = (
    "message_id",
    "feature_name",
    "feature_value",
    "category",
    "is_open_ended",
    "evidence_span",
    "rationale",
)
_CLASSIFIER_WORKERS = 16
_MAX_COVERAGE_ROUNDS = 4
_SINGLE_POST_BATCH_SIZE = 1


def _utc_stamp() -> str:
    """Return a filesystem-safe UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H:%M:%S.%f")


def _load_cohort(path: Path) -> pd.DataFrame:
    """Load the four-cell cohort.

    Parameters
    ----------
    path
        Cohort CSV path.

    Returns
    -------
    pandas.DataFrame
        Cohort frame.

    Raises
    ------
    FileNotFoundError
        When the cohort file is missing.
    """
    if not path.is_file():
        raise FileNotFoundError(path.resolve())
    return pd.read_csv(path)


def _newest_run_dir(outputs_dir: Path) -> Path | None:
    """Return the newest run directory under a class outputs folder.

    Parameters
    ----------
    outputs_dir
        ``.../keep/outputs`` or ``.../remove/outputs``.

    Returns
    -------
    pathlib.Path or None
        Newest child directory, or None when absent.
    """
    if not outputs_dir.is_dir():
        return None
    runs = sorted(path for path in outputs_dir.iterdir() if path.is_dir())
    if not runs:
        return None
    return runs[-1]


def _parse_batch_features(path: Path) -> list[dict[str, Any]]:
    """Parse feature rows from one Stage 1 batch JSON file.

    Parameters
    ----------
    path
        Batch JSON path.

    Returns
    -------
    list[dict[str, Any]]
        Feature dictionaries with frozen fields.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("result", {}).get("features", [])
    rows: list[dict[str, Any]] = []
    for feat in features:
        row = {field: feat.get(field) for field in _FEATURE_FIELDS}
        row["message_id"] = str(row["message_id"])
        if isinstance(row.get("category"), dict):
            row["category"] = row["category"].get("value", row["category"])
        rows.append(row)
    return rows


def _load_prior_features(
    prior_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load newest-run Stage 1 features for keep and remove classes.

    Parameters
    ----------
    prior_root
        Prior experiment generated_features root.

    Returns
    -------
    tuple[list[dict[str, Any]], dict[str, str]]
        Feature rows and message_id to chosen run path.
    """
    rows: list[dict[str, Any]] = []
    chosen_runs: dict[str, str] = {}
    for label in (LabelClass.KEEP.value, LabelClass.REMOVE.value):
        run_dir = _newest_run_dir(prior_root / label / "outputs")
        if run_dir is None:
            continue
        for path in sorted(run_dir.glob("*.json")):
            if path.name == "metadata.json":
                continue
            for feat in _parse_batch_features(path):
                message_id = str(feat["message_id"])
                chosen_runs[message_id] = str(run_dir)
                rows.append(feat)
    return rows, chosen_runs


def _cell_to_label_class(cell: str) -> LabelClass:
    """Map a four-cell label to keep or remove for Stage 1 prompts.

    Parameters
    ----------
    cell
        Four-cell string.

    Returns
    -------
    LabelClass
        keep or remove.

    Raises
    ------
    ValueError
        When ``cell`` is unknown.
    """
    if cell in _KEEP_CELLS:
        return LabelClass.KEEP
    if cell in _REMOVE_CELLS:
        return LabelClass.REMOVE
    raise ValueError(f"Unknown cell {cell!r}")


def _form_batches(
    posts: pd.DataFrame,
    posts_per_batch: int,
) -> list[dict[str, Any]]:
    """Form Stage 1 batches, including a smaller final remainder batch.

    Parameters
    ----------
    posts
        Missing posts with message_id, original_text, mirror_text, cell.
    posts_per_batch
        Target batch size.

    Returns
    -------
    list[dict[str, Any]]
        Runner batch dictionaries.

    Raises
    ------
    ValueError
        When ``posts_per_batch`` is not positive.
    """
    if posts_per_batch <= 0:
        raise ValueError(f"posts_per_batch must be positive, got {posts_per_batch}")
    if posts.empty:
        return []

    batches: list[dict[str, Any]] = []
    batch_id = 0
    for start in range(0, len(posts), posts_per_batch):
        slice_df = posts.iloc[start : start + posts_per_batch]
        label_classes = {
            _cell_to_label_class(str(cell)) for cell in slice_df["cell"].tolist()
        }
        if len(label_classes) != 1:
            raise ValueError(
                "Each Stage 1 batch must contain a single keep/remove label class"
            )
        label_class = next(iter(label_classes))
        batch_posts = [
            {
                "message_id": str(row["message_id"]),
                "original_text": str(row["original_text"]),
                "mirror_text": str(row["mirror_text"]),
                "decision": label_class.value,
            }
            for _, row in slice_df.iterrows()
        ]
        batches.append(
            {
                "batch_id": batch_id,
                "label_class": label_class.value,
                "message_ids": sorted(post["message_id"] for post in batch_posts),
                "posts": batch_posts,
            }
        )
        batch_id += 1
    return batches


def _run_one_batch(
    batch: dict[str, Any],
    model: str,
    output_dir: Path,
    index: int,
) -> list[dict[str, Any]]:
    """Run one Stage 1 batch and write its JSON under this experiment.

    Parameters
    ----------
    batch
        Dual-text Stage 1 batch payload.
    model
        OpenAI model id.
    output_dir
        Destination run directory.
    index
        Zero-padded file index.

    Returns
    -------
    list[dict[str, Any]]
        Parsed feature rows from the batch result.
    """
    llm = LLMService()
    messages = prompt_fn(batch)
    result = llm.structured_completion(
        messages=messages,
        response_model=SingleClassBatchFeatureGeneration,
        model=model,
    )
    out = writer_map_fn(batch, result)
    stamp = _utc_stamp()
    path = output_dir / f"{index:05d}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return _parse_batch_features(path)


def _generate_features_for_posts(
    posts: pd.DataFrame,
    model: str,
    posts_per_batch: int,
    workers: int,
) -> list[dict[str, Any]]:
    """Generate Stage 1 features for missing posts under this experiment.

    Parameters
    ----------
    posts
        Missing cohort posts.
    model
        OpenAI model id.
    posts_per_batch
        Batch size; final remainder batches are still sent.
    workers
        Concurrent LLM workers.

    Returns
    -------
    list[dict[str, Any]]
        Newly generated feature rows.
    """
    if posts.empty:
        return []

    keep_posts = posts[posts["cell"].isin(_KEEP_CELLS)].reset_index(drop=True)
    remove_posts = posts[posts["cell"].isin(_REMOVE_CELLS)].reset_index(drop=True)
    batches = _form_batches(keep_posts, posts_per_batch) + _form_batches(
        remove_posts, posts_per_batch
    )
    run_dir = GENERATED_ROOT / "outputs" / _utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "model": model,
        "posts_per_batch": posts_per_batch,
        "n_posts": int(len(posts)),
        "n_batches": len(batches),
        "message_ids": sorted(posts["message_id"].astype(str).tolist()),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    generated: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(_run_one_batch, batch, model, run_dir, index): index
            for index, batch in enumerate(batches)
        }
        for future in tqdm(
            as_completed(future_to_index),
            total=len(future_to_index),
            desc="Stage 1 missing features",
        ):
            generated.extend(future.result())
    return generated


def _attach_cell(
    features: list[dict[str, Any]],
    cell_by_id: dict[str, str],
) -> list[dict[str, Any]]:
    """Join cohort cell onto feature rows for cohort message ids only.

    Parameters
    ----------
    features
        Stage 1 feature rows.
    cell_by_id
        Mapping from message_id to cell.

    Returns
    -------
    list[dict[str, Any]]
        Feature rows with ``cell`` for cohort posts.
    """
    out: list[dict[str, Any]] = []
    for feat in features:
        message_id = str(feat["message_id"])
        if message_id not in cell_by_id:
            continue
        row = dict(feat)
        row["cell"] = cell_by_id[message_id]
        out.append(row)
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write one JSON object per line.

    Parameters
    ----------
    path
        Destination JSONL path.
    rows
        Feature rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def run_analysis2_features(
    cohort_path: Path = COHORT_CSV,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Reuse prior Stage 1 features and generate only missing cohort posts.

    Parameters
    ----------
    cohort_path
        Four-cell cohort CSV.
    model
        OpenAI model id for new generation.

    Returns
    -------
    dict[str, Any]
        Coverage summary written to ``coverage.json``.
    """
    cohort = _load_cohort(cohort_path)
    cell_by_id = {
        str(row["message_id"]): str(row["cell"]) for _, row in cohort.iterrows()
    }
    cohort_ids = set(cell_by_id)
    prior_rows, chosen_runs = _load_prior_features(PRIOR_FEATURES_ROOT)
    reused_rows = _attach_cell(prior_rows, cell_by_id)
    covered_ids = {str(row["message_id"]) for row in reused_rows}
    missing_ids = sorted(cohort_ids - covered_ids)

    generated_rows: list[dict[str, Any]] = []
    remaining = missing_ids
    for round_idx in range(_MAX_COVERAGE_ROUNDS):
        if not remaining:
            break
        posts = cohort[cohort["message_id"].astype(str).isin(remaining)].copy()
        posts_per_batch = (
            DEFAULT_POSTS_PER_BATCH if round_idx == 0 else _SINGLE_POST_BATCH_SIZE
        )
        print(
            f"coverage_round={round_idx} missing={len(remaining)} "
            f"posts_per_batch={posts_per_batch}"
        )
        new_rows = _generate_features_for_posts(
            posts,
            model,
            posts_per_batch,
            _CLASSIFIER_WORKERS,
        )
        new_rows = _attach_cell(new_rows, cell_by_id)
        generated_rows.extend(new_rows)
        covered_ids |= {str(row["message_id"]) for row in new_rows}
        remaining = sorted(cohort_ids - covered_ids)

    merged = reused_rows + generated_rows
    ANALYSIS2_DIR.mkdir(parents=True, exist_ok=True)
    _write_jsonl(MERGED_FEATURES_JSONL, merged)

    coverage = {
        "cohort_n": len(cohort_ids),
        "reused_n": len({str(row["message_id"]) for row in reused_rows}),
        "generated_n": len({str(row["message_id"]) for row in generated_rows}),
        "missing_after_run_n": len(remaining),
        "prior_runs_used": sorted(set(chosen_runs.values())),
        "merged_feature_rows": len(merged),
    }
    COVERAGE_JSON.write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    if remaining:
        raise RuntimeError(
            "Stage 1 coverage incomplete after generation rounds. "
            f"missing_after_run_n={len(remaining)} examples={remaining[:10]}"
        )
    return coverage


def main() -> None:
    """CLI entry: merge reused and newly generated Stage 1 features."""
    coverage = run_analysis2_features(COHORT_CSV, DEFAULT_MODEL)
    print(json.dumps({k: coverage[k] for k in (
        "cohort_n",
        "reused_n",
        "generated_n",
        "missing_after_run_n",
        "merged_feature_rows",
    )}, indent=2))
    print(f"Wrote {MERGED_FEATURES_JSONL}")
    print(f"Wrote {COVERAGE_JSON}")


if __name__ == "__main__":
    main()
