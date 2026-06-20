# Truncation v5: full-dataset topic-aligned regeneration

We got cleared to apply the **topic-alignment prompt intervention** from `truncation_v4/` beyond the manual-review sample.

## What v5 does

v5 regenerates **mirrored posts for the full dataset** in:

`experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv`

For each row, it:

1. Generates a new mirror from `original_text` using the base `FLIP_PROMPT` plus:

> Keep the mirror on the same political topic/issue as the original and flip only the stance, not the subject — switch to a different issue only when the original's topic has no natural opposite-stance position.

2. Writes both:
   - `raw_mirrored_text`: direct model output
   - `processed_mirrored_text`: v3 sentence-first truncation (`max_chars=300`, `sentence_overflow=20`)

## Idempotency / retry-safety

`generate_flips.py` is **append-only** and **resume-safe**:

- Output is written to `outputs/truncation_v5/flips.csv`
- On reruns, it loads the set of already-written `post_primary_key` values and skips them
- Progress is shown with `tqdm`

## Run

From repo root:

```bash
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py --max-posts 10 --force
```

