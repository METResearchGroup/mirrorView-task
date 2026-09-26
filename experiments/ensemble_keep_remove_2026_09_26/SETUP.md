# Setup

## Data used by `preliminary_analysis.py`

- `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`, loaded with `shared.data.dataloader.load_dataset`. The script keeps moderation trials with a post id and a keep or remove decision, one decision per rater and post, using the helpers in `experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`.
- `s3://mirrorview-experimental-artifacts/experiments/compare_jev_human_uncertainty_2026_09_25/outputs/joined.parquet`, the stored Jev A1 pair probabilities joined to five-rater vote counts (15,113 posts).

Run from the repo root with the lab AWS credentials exported as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`:

```bash
PYTHONPATH=. uv run python experiments/ensemble_keep_remove_2026_09_26/preliminary_analysis.py
```

## Data needed by the proposed stages

- The same session export, for rater decisions, `phase1_pair_reflection_text`, demographics, policy attitudes, and `attention_check_passed`.
- The PR 310 post split (seed 1, 80/20) and the LoRA adapters under `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/`.
- The Jev A1 pair probabilities above, for the recalibrated baseline and the routing score.
- LLM post features to be generated in Stage 1, starting from `experiments/create_llm_features_2026_08_05/` and the GEPA criteria from PR 309.
