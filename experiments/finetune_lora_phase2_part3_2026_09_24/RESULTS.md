# Part 3 LoRA cross-eval keep/remove results

Cross-eval scoring has not been run yet. Prediction CSVs from SageMaker inference
are not available in this environment.

After baseline and fine-tuned prediction files exist locally, run:

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py \
  --write-results experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md
```

Running score_all.py writes `experiment4_cross_eval/scores/cross_eval.csv` and
replaces this file with the full remove-F1 matrix, metrics table, split counts,
and Part 2 reference block.
