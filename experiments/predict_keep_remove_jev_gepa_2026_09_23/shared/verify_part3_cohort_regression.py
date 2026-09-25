"""Live regression check for frozen Part 3 cohort A counts and split hash.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python \\
        experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/verify_part3_cohort_regression.py
"""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import (
    EXPECTED_COHORT_KEEP,
    EXPECTED_COHORT_POSTS,
    EXPECTED_COHORT_REMOVE,
    PART3_FROZEN_SPLIT_HASH,
    build_part3_split_frame,
    compute_split_hash,
    _cohort_counts_from_frame,
)


def main() -> None:
    frame = build_part3_split_frame()
    counts = _cohort_counts_from_frame(frame)
    split_hash = compute_split_hash(frame)
    if counts.n_posts != EXPECTED_COHORT_POSTS:
        raise SystemExit(f"unexpected cohort posts: {counts.n_posts}")
    if counts.n_keep != EXPECTED_COHORT_KEEP:
        raise SystemExit(f"unexpected cohort keep: {counts.n_keep}")
    if counts.n_remove != EXPECTED_COHORT_REMOVE:
        raise SystemExit(f"unexpected cohort remove: {counts.n_remove}")
    if split_hash != PART3_FROZEN_SPLIT_HASH:
        raise SystemExit(f"unexpected split hash: {split_hash}")
    print("part3_cohort_regression_ok")


if __name__ == "__main__":
    main()
