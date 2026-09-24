"""Live and offline union pair token measurement for rebuilt GEPA cost estimates.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/measure_tokens.py --view pair --n-posts 100 --output experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/_smoke/token_measurement.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevDataInst,
    JevGepaRebuiltAdapter,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import GEPA_SEED
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.pricing import estimate_jev_cost_usd
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import default_study_instruction_seed
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET

StudyFlipScorer = Callable[..., jev_scorer.BatchResult]
FULL_BUDGET_POSTS = 30_000
MEASUREMENT_BATCH_SIZE = 10


def measure_union_pair_tokens(
    pool: list[JevDataInst],
    *,
    view: str,
    n_posts: int,
    study_instruction: str,
    scorer: StudyFlipScorer,
    rng_seed: int,
    client: Any | None = None,
) -> dict[str, float | int | str]:
    """Score a random subsample and summarize per-post input token usage."""
    if n_posts <= 0:
        raise ValueError("n_posts must be positive")
    if len(pool) < n_posts:
        raise ValueError(f"pool size {len(pool)} smaller than n_posts {n_posts}")

    rng = np.random.default_rng(rng_seed)
    indices = rng.choice(len(pool), size=n_posts, replace=False)
    sample = [pool[int(index)] for index in indices]

    adapter = JevGepaRebuiltAdapter(
        view=view,  # type: ignore[arg-type]
        scorer=scorer,
        client=client,
        batch_size=MEASUREMENT_BATCH_SIZE,
    )
    per_post_tokens: list[float] = []
    for chunk_start in range(0, len(sample), MEASUREMENT_BATCH_SIZE):
        chunk = sample[chunk_start : chunk_start + MEASUREMENT_BATCH_SIZE]
        state_texts = [adapter._render_state_text(instance) for instance in chunk]  # noqa: SLF001
        batch_result = scorer(
            client,
            state_texts,
            view,
            study_instruction=study_instruction,
        )
        per_post = batch_result.input_tokens / len(chunk)
        per_post_tokens.extend([per_post] * len(chunk))

    token_array = np.array(per_post_tokens, dtype=float)
    mean_tokens = float(token_array.mean())
    return {
        "n_posts": n_posts,
        "view": view,
        "mean_input_tokens_per_post": mean_tokens,
        "p50_input_tokens_per_post": float(np.percentile(token_array, 50)),
        "p90_input_tokens_per_post": float(np.percentile(token_array, 90)),
        "jev_optimize_usd_per_30k_posts": estimate_jev_cost_usd(
            int(round(FULL_BUDGET_POSTS * mean_tokens)),
            0,
        ),
        "cohort_parquet": Path(COHORT_UNION_PARQUET).name,
    }


def _load_measurement_pool() -> list[JevDataInst]:
    from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.splits import (
        load_gepa_union_splits,
    )

    trainset, valset = load_gepa_union_splits()
    return trainset + valset


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for union pair token measurement."""
    parser = argparse.ArgumentParser(description="Measure Jev input tokens per post on union cohort")
    parser.add_argument("--view", default="pair", choices=("pair", "original", "mirror"))
    parser.add_argument("--n-posts", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=GEPA_SEED)
    args = parser.parse_args(argv)

    pool = _load_measurement_pool()
    study_instruction = default_study_instruction_seed(args.view)
    from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets import get_jev_api_key

    client = jev_scorer.build_client(get_jev_api_key())
    payload = measure_union_pair_tokens(
        pool,
        view=args.view,
        n_posts=args.n_posts,
        study_instruction=study_instruction,
        scorer=jev_scorer.score_batch_with_study_instruction,
        rng_seed=args.seed,
        client=client,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main(sys.argv[1:])
