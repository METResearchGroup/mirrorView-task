# Part 2+3 LoRA cross-eval keep/remove results

Data: Study Phase 2 Part 2 and Part 3 union labels (`STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` and `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3`). Seed 1 splits: modal pool 20,000 posts, unanimous pool 5,715; Exp 1/3 train 702 rows each, Exp 2 train 7,686, unanimous test 168, modal test 1,922.

Cross-eval scoring has not been run yet. Prediction CSVs from SageMaker inference are not available in this environment.

After baseline and fine-tuned prediction files exist locally, run:

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py \
  --write-results experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md
```

Running score_all.py writes `experiment4_cross_eval/scores/cross_eval.csv` and replaces this file with the full remove-F1 matrix, metrics table, split counts, and Part 2 reference block.
