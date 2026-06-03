# Removal rate by party × sampled toxicity

Source: `scripts/mirrorview_pilot_data_2026_04_28-16:31:47.csv` (newest export; same discovery rule as `summary_stats.py`).

Slice: moderation trials, phases 1–2, `decision` ∈ {keep, remove}, party and condition filters aligned with `summary_stats` phase tables — see `toxicity_remove_breakdown.py`.

## `prop_remove` by `sample_toxicity_type` (wide)

| sample_toxicity_type   | democrat | republican |
|------------------------|----------|------------|
| sample_low_toxicity    | 0.1648   | 0.1785     |
| sample_middle_toxicity | 0.2825   | 0.3027     |
| sample_high_toxicity   | 0.5219   | 0.5520     |

## Counts (same slice)

| sample_toxicity_type   | n_trials (democrat) | n_remove (democrat) | n_trials (republican) | n_remove (republican) |
|------------------------|--------------------:|--------------------:|----------------------:|----------------------:|
| sample_low_toxicity    | 5120                | 844                 | 4920                  | 878                   |
| sample_middle_toxicity | 10240               | 2893                | 9840                  | 2979                  |
| sample_high_toxicity   | 5120                | 2672                | 4920                  | 2716                  |

Refresh: run `PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py` after updating the export, then update this file if numbers shift.
