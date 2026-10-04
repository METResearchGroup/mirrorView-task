# Setup

Run from the repository root. `run_ablations.py` is the entry point. It builds the Docker image once, pushes that tag, and starts the three training jobs.

```bash
HF_JOB_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest \
    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/run_ablations.py
```

`HF_JOB_IMAGE` is the registry tag Hugging Face Jobs pulls. Log in to that registry before the push. The job receives `HF_TOKEN`, `WANDB_API_KEY`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` from `EnvVarsContainer` in `lib/load_env_vars.py`.

Each job uses one A10G (`a10g-large`) and a 2-day timeout. Training is 3 epochs, micro-batch 1, gradient accumulation 8, and 8-bit Adam. The saved adapter is uploaded to `s3://mirrorview-experimental-artifacts/experiments/lora_finetuning_study2_2026_10_04/<run_name>/` before the job exits.

Each job trains on one upsampled label set and records a separate Weights & Biases project:

| Ablation | Training table | Project |
| --- | --- | --- |
| unanimous | `UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` | `lora_finetuning_study2_2026_10_04_unanimous` |
| split | `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | `lora_finetuning_study2_2026_10_04_split` |
| all | `UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS` | `lora_finetuning_study2_2026_10_04_all` |

# Data

Training and prediction tables are CSVs in `s3://mirrorview-experimental-artifacts`. The object key is the path in `shared/data/registry.py`. `shared/data/dataloader.py` loads a registry name from that bucket.

Training uses the upsampled tables:

- `shared/data/transformed/study_2/upsampled_keep_remove_unanimous_labels.csv`
- `shared/data/transformed/study_2/upsampled_keep_remove_split_labels.csv`
- `shared/data/transformed/study_2/upsampled_keep_remove_labels.csv`

The README also names the prediction tables. Those objects are:

- `shared/data/transformed/study_2/keep_remove_unanimous_labels.csv`
- `shared/data/transformed/study_2/keep_remove_split_labels.csv`
- `shared/data/transformed/study_2/keep_remove_labels.csv`

# Key files

| File | Role |
| --- | --- |
| `run_ablations.py` | Builds the image once and submits the three jobs. |
| `run_job.py` | Image build, push, and the job settings for one `train.py` command. |
| `train.py` | LoRA training for the dataset, project, and group passed on the command line. |
| `dataloader.py` | Turns one registered label table into TRL prompt-completion rows. |
| `Dockerfile` | Image that contains this experiment, `shared/`, and `lib/`. |
| `shared/models/llm/prompt.py` | Keep/remove system string and study prompt. |
| `shared/models/llm/training/lora_training.py` | TRL `SFTTrainer` loop and Weights & Biases logging. |
| `shared/models/llm/infra/upload_to_hf_jobs.py` | Submits an image and job settings to Hugging Face Jobs. |
