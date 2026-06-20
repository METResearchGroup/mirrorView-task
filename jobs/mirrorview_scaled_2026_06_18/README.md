# MirrorView scaled, 2026-06-18

Here we have three related CSVs:

- `old_flips.csv`: the original dataset version (mirrors tend to be too long).
- `full_new_flips.csv`: the full regeneration output that includes both `raw_mirrored_text` and `processed_mirrored_text`. **Note:** in this file, `original_text` has been **truncated using the same truncation strategy as the mirrored posts** (sentence-first v3 truncation), so any mirror−original comparisons against this file are against **truncated originals**.
- `flips.csv`: the cleaned export derived from `full_new_flips.csv` (uses `processed_mirrored_text` as `mirrored_text`, drops `raw_mirrored_text`). Because it is derived from `full_new_flips.csv`, its `original_text` is also the **truncated** version.

## Verification: average character counts

Run:

```bash
PYTHONPATH=. uv run python jobs/mirrorview_scaled_2026_06_18/compare_avg_char_lengths.py
```

Results:

- `old_flips.csv`: avg original chars **247.5**, avg mirrored chars **327.0**
- `full_new_flips.csv`:
  - avg original chars (**truncated**) **179.2**
  - avg raw mirrored chars **294.0**
  - avg processed mirrored chars **200.2**
- `flips.csv`: avg original chars (**truncated**) **179.2**, avg mirrored chars **200.2**
- Delta (`flips.csv` − `old_flips.csv`): avg mirrored chars **−126.8**
