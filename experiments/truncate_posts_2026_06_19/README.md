# Truncating posts

We've been doing experiments in `match_lengths_original_mirrors_2026_06_19/` to try to get the original and LLM-generated outputs to be approximately the same length. A simpler approach is to truncate both sides at the last sentence boundary before a char limit.

This experiment applies that strategy in `truncate_flips.py` to
`experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv`.

**Truncation limits:** original = 300 chars, mirrored = 300 chars (sentence-aware: cut at the last `.` within the window).

## Usage

```bash
# Writes truncated_flips.csv and truncated_flips_with_flag.csv
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py

# Single custom output, optionally with is_truncated column
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py -o out.csv
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py -o out.csv --include-truncated-flag
```

Outputs:

- `truncated_flips.csv` — same columns as source (for export; rename to `flips.csv` as needed)
- `truncated_flips_with_flag.csv` — adds `is_truncated` column

## Results (10,000 posts)

**Rows truncated:** 5,682 (56.8%)

### All posts

| Metric | Before | After |
|---|---|---|
| Avg original length | 247.5 chars | 188.7 chars |
| Avg mirrored length | 327.0 chars | 204.9 chars |
| ≥10% length diff | 8,686 (86.9%) | 7,563 (75.6%) |

### Truncated posts only (`is_truncated=True`, 5,682)

| Metric | Before | After |
|---|---|---|
| Avg original length | 326.7 chars | 223.2 chars |
| Avg mirrored length | 432.8 chars | 218.0 chars |
| ≥10% length diff | 5,175 (91.1%) | 4,052 (71.3%) |

### All posts by political lean (`sampled_stance`)

| | Left (6,550) | Right (3,450) |
|---|---|---|
| **Before avg original / mirrored** | 249.1 / 326.9 | 244.6 / 327.1 |
| **After avg original / mirrored** | 190.9 / 204.8 | 184.5 / 205.2 |
| **≥10% length diff (before)** | 5,642 (86.1%) | 3,044 (88.2%) |
| **≥10% length diff (after)** | 4,899 (74.8%) | 2,664 (77.2%) |

### Truncated posts only by political lean

| | Left (3,592) | Right (2,090) |
|---|---|---|
| **Before avg original / mirrored** | 334.9 / 441.3 | 312.7 / 418.1 |
| **After avg original / mirrored** | 228.8 / 218.7 | 213.6 / 216.9 |
| **≥10% length diff (before)** | 3,258 (90.7%) | 1,917 (91.7%) |
| **≥10% length diff (after)** | 2,515 (70.0%) | 1,537 (73.5%) |

Equal 300-char limits on both sides improve overall length parity from 86.9% to 75.6% of pairs differing by ≥10%. Among truncated rows, mirrored text ends slightly shorter on average than originals (218.0 vs 223.2 chars). Left-leaning posts show slightly better parity after truncation than right-leaning posts.
