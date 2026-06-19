# Experiments for matching mirror lengths to original post lengths

We want the lengths of the MirrorView mirrors to approximately match the original posts.

## Context

MirrorView presents participants with social media posts and their politically mirrored counterparts. If mirrors are systematically longer or shorter than the originals, length becomes a confound: participants might react to verbosity or brevity rather than the intended stance flip.

The scaled mirror generation pipeline (`experiments/scaled_mirrors_generation_2026_06_02/`) produces flips via Bedrock (Claude Sonnet) using a structured JSON response (`flipped_text` + `explanation`). A validation pass on the combined production flips (`validate_mirrors_equal_lengths.py`) found that **86.9%** of mirrors differ from their originals by ≥10% in character length (avg original: 247.5 chars; avg mirrored: 327.0 chars).

This folder holds small, fast experiments to test interventions before changing the production flip pipeline.

## v1 — length requirement in the prompt

**Hypothesis:** Adding an explicit instruction to match original post length will reduce length drift.

**Intervention:** Use the standard `FLIP_PROMPT` from `experiments/scaled_mirrors_generation_2026_06_02/prompts.py`, which includes:

> The length of the mirror should be about the same as the original post.

**Method:**

1. Load `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv`.
2. Randomly sample 50 posts (`random_state=42`) using `original_text` (not the existing mirrored text).
3. Regenerate flips with the same Bedrock chain as `generate_flips.py` (batch size 25, max concurrency 10).
4. Write results to `outputs/match_lengths/{timestamp}.csv`.
5. Validate length parity using the same ≥10% relative character-length check as `validate_mirrors_equal_lengths.py`.

**Run:**

```bash
PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py
```

**Results (2026-06-19 run):**

| Metric | Production flips (n=10,000) | v1 sample (n=50) |
|---|---|---|
| Avg original length (chars) | 247.5 | 296.0 |
| Avg mirrored length (chars) | 327.0 | 339.2 |
| Posts failing ≥10% length check | 86.9% | 76.0% |

Output: `outputs/match_lengths/2026_06_19-15:01:18.csv`

**Conclusion:** The prompt-only instruction helps slightly (76% vs 87% failure rate) but is not sufficient. Mirrors still tend to run long, and most posts fail the parity check.
