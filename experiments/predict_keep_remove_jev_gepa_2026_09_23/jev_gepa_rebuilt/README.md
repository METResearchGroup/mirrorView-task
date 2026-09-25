Rebuilt GEPA on the Part 2 plus Part 3 union cohort. See `../SETUP.md` and `../RESULTS.md`. The plan is `docs/plans/2026-09-24_rebuilt_gepa_union_66a982/`.

Smoke (120 scored posts) and the R4 round-robin check:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --smoke
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/run_ablations.py --wave r4
```

Production optimize, then one test read of the selected candidate:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --max-metric-calls 30000
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py --ablation-id R1_gepa_pair --split test
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/summarize_results.py --ablation-ids R1_gepa_pair --write-results-md
```

R5 and R6 use 15,000 scored posts. Launch them with `run_ablations.py --wave r5_r6` after R1 dev-B F1 is above 0.538.
