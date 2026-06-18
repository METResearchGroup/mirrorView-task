# Combined balanced flips

## Purpose

This folder holds a single subsampled mirror-flip dataset produced by
`balance_flips.py`. The two source flip runs contained more rows than needed and
did not match the desired toxicity mix (the newer run was ~33/33/33 low/middle/high).
`balance_flips.py` merges them, deduplicates on `post_primary_key`, and samples
10,000 rows with a **25/50/25** low/middle/high toxicity split. Within each
toxicity tier, Twitter rows are prioritized and remaining slots are split 50/50
between Bluesky and Reddit.

## Source files

Patched flip CSVs (Reddit ``post_primary_key`` corrected to ``unique_reddit_id``):

- `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/2026_06_12-12:44:13/edited_flips.csv`
- `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/2026_06_17-14:50:48/edited_flips.csv`

Produced from the original ``flips.csv`` files via
``fix_primary_key_column_for_reddit_posts.py``.

Original (pre-patch) sources:

- `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/2026_06_12-12:44:13/flips.csv`
- `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/2026_06_17-14:50:48/flips.csv`

On duplicate `post_primary_key` values, the row from the newer file
(`2026_06_17-14:50:48`) is kept.

## Output

- `flips.csv` — balanced sample (columns: `post_primary_key`, `original_text`,
  `sample_toxicity_type`, `sampled_stance`, `mirrored_text`)

## Regenerate

```bash
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/fix_primary_key_column_for_reddit_posts.py
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/balance_flips.py
```
