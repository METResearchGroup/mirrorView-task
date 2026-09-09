# Upsample right-leaning high toxicity posts

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Take the 2,000 unused medium toxicity posts first. Then take the rest of the cleaned medium posts, keep the right-leaning rows, and drop ids from pull request 260. Score those leftover posts with the Perspective API. Reclassify the 300 highest scores as high. Write those 300 rows and a unified 2,300 post table (2,000 medium plus 300 right-high).

`GOOGLE_API_KEY` is required. Scoring uses it through `EnvVarsContainer`.

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
```

Expected stdout includes `candidate_rows=` at least 300, `promotions=300`, `unified_rows=2300`, `unified_medium=2000`, and `unified_high=300`.
