"""Live smoke test for the LLM feature-generation experiment."""

from __future__ import annotations

from experiments.llm_based_feature_generation_2026_07_31.main import run_pipeline

# Enough stratified sample to form one 10+10 batch (ceil keeps/removes >= 10 each).
SMOKE_SAMPLE_FRACTION = 0.005
SMOKE_KEEP_PER_BATCH = 10
SMOKE_REMOVE_PER_BATCH = 10
SMOKE_SEED = 42


def main() -> int:
    """Run one live 10 keep + 10 remove batch through the real CLI pipeline."""
    argv = [
        "--sample-fraction",
        str(SMOKE_SAMPLE_FRACTION),
        "--keep-per-batch",
        str(SMOKE_KEEP_PER_BATCH),
        "--remove-per-batch",
        str(SMOKE_REMOVE_PER_BATCH),
        "--seed",
        str(SMOKE_SEED),
    ]
    print("smoke argv:", " ".join(argv))
    run_pipeline(
        sample_fraction=SMOKE_SAMPLE_FRACTION,
        seed=SMOKE_SEED,
        keep_per_batch=SMOKE_KEEP_PER_BATCH,
        remove_per_batch=SMOKE_REMOVE_PER_BATCH,
        model="gpt-5.4-nano",
        exclude_ids_from=None,
        stage1_only=False,
        stage2_only=False,
        stage1_dir=None,
    )
    print("smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
