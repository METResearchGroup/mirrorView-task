# LoRA fine-tuning for Study 2

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Steps:

1. Create dataset.
2. Define the image.
3. Build the image.
4. Upload to hf jobs

We want to train on two sets of labels:

- Ablation 1: Train on only unanimous labels (found in `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`)
- Ablation 2: Train on only split labels (found in `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`)
- Ablation 3: Train on all modal labels (found in `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS`)

For each ablation, we run predictions on the following sets of data:

- Unanimous labels (found in `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`)
- Split labels (found in `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`)
- All (modal) labels (found in `STUDY_2_KEEP_REMOVE_LABELS`)
