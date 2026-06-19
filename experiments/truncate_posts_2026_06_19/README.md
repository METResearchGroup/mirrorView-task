# Truncating posts

We've been doing experiments in `match_lengths_original_mirrors_2026_06_19/` to try to get the original and LLM-generated outputs to be approximately the same. But then I realized we can just truncate on the latest sentence threshold before the max char count and we're OK.

We do this here, in `truncate_flips.py`, and save to `truncated_flips.csv` (which gets renamed to `flips.csv` for ease of export).
