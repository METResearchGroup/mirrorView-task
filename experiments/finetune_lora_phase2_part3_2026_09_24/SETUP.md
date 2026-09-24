# Part 3 LoRA fine-tune — setup

## Prerequisites

Step 1 label CSVs and registry keys:

- `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` — modal labels (18,862 posts: 13,629 keep / 5,233 remove; includes `n_raters`)
- `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` — unanimous min-3 labels (4,988 posts: 4,497 keep / 491 remove)

## Post-level split and balance rules

1. Assign train and test once at **post level** on the modal label pool, stratified by modal `decision`, 80/20, seed 1 (`n_train = int(0.8 * n_class)` per class).
2. Write `data/split_manifest.csv` with columns `post_id`, `split`, `modal_label`, `in_unanimous`.
3. Unanimous train/test are subsets of modal train/test post ids (same unanimous-min3 label rows, filtered by manifest split).
4. Balance each split with all removes plus equal sampled keeps (seed 1), reusing `balance_keep_remove` from `experiments/finetune_qwen_model_2026_08_08`.
5. Experiment 1 train uses unanimous train posts; Experiment 2 train uses modal train posts.
6. Experiment 3 samples from Experiment 2 balanced modal train to match Experiment 1 row and remove counts (seed 1, 1:1 balance).
7. Shared test CSVs: `data/test_unanimous.csv` (unanimous test posts), `data/test_modal.csv` (modal test posts).

## Approximate output counts (seed 1)

| Output | Approximate rows |
| --- | ---: |
| Experiment 1 train | 808 (404 keep + 404 remove) |
| Experiment 2 train | 8,372 |
| Experiment 3 train | 808 (matches Exp 1) |
| Unanimous test | 174 (87 + 87) |
| Modal test | 2,094 (1,047 + 1,047) |

Exact counts print when `build_splits.py` runs.

## S3 storage

- Bucket: `mirrorview-experimental-artifacts`
- Prefix: `experiments/finetune_lora_phase2_part3_2026_09_24/`

## Main caller commands

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/finetune_lora_phase2_part3_2026_09_24/tests -q
```

Build splits:

```bash
PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py --force
```

Build chat datasets:

```bash
PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py --force
```

Upload data (export AWS credentials per `AGENTS.md` first):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for dir in data experiment1_unanimous/data experiment2_modal/data experiment3_modal_size_matched/data; do
  aws s3 sync "experiments/finetune_lora_phase2_part3_2026_09_24/${dir}/" \
    "s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/${dir}/" \
    --region us-east-2
done
```
