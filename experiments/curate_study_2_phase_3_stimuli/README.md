# Curate study 2 phase 3 stimuli

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Join the 10,200 post sample to its existing flips, and join the unified 2,300 posts to the new flips. Count posts that have a flip in each political stance by toxicity cell. If any cell is short of its target, print the available counts, write RESULTS.md, exit 1, and do not write `flips.csv`. If every cell meets its target, sample 10,000 posts and write `flips.csv`.

Cell targets, even left and right split:

| political_stance | low | medium | high | total |
| ---------------- | --: | -----: | ---: | ----: |
| left | 1250 | 2500 | 1250 | 5000 |
| right | 1250 | 2500 | 1250 | 5000 |
| total | 2500 | 5000 | 2500 | 10000 |

Output columns, in this order: `post_primary_key`, `original_text`, `sample_toxicity_type`, `sampled_stance`, `mirrored_text`. Map toxicity `low` to `sample_low_toxicity`, `medium` to `sample_middle_toxicity`, and `high` to `sample_high_toxicity`.

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
```
