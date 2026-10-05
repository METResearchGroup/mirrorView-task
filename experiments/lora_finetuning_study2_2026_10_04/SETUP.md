# Setup

Run from the repository root. `run_ablations.py` is the entry point. It builds the Docker image once, pushes that tag, and starts the three training jobs.

```bash
HF_JOB_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest \
    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/run_ablations.py
```

`HF_JOB_IMAGE` is the registry tag Hugging Face Jobs pulls. Log in to that registry before the push. The job receives `HF_TOKEN`, `WANDB_API_KEY`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` from `EnvVarsContainer` in `lib/load_env_vars.py`.

After training, the saved LoRA adapter is uploaded to `s3://mirrorview-experimental-artifacts/experiments/lora_finetuning_study2_2026_10_04/adapters/{group}/{run_name}/`, where `{group}` is the ablation (`unanimous`, `split`, or `all`) and `{run_name}` is the Weights & Biases run name (`Qwen3.5-4B_lora_{group}_{timestamp}`).

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
| `evaluate.py` | vLLM eval launcher and in-job scorer (`HF_EVAL_IMAGE`, flavor `l4x1`). |
| `dataloader.py` | Turns one registered label table into TRL prompt-completion rows. |
| `Dockerfile` | Training image (torch 2.6 + linear-attention kernels). |
| `Dockerfile.eval` | Eval image (`vllm/vllm-openai:v0.26.0` + this experiment). |
| `shared/models/llm/prompt.py` | Keep/remove system string and study prompt. |
| `shared/models/llm/training/lora_training.py` | TRL `SFTTrainer` loop and Weights & Biases logging. |
| `shared/models/llm/infra/upload_to_hf_jobs.py` | Submits an image and job settings to Hugging Face Jobs. |

# Evaluate

After an adapter exists under `s3://mirrorview-experimental-artifacts/experiments/lora_finetuning_study2_2026_10_04/adapters/{ablation}/{run_name}/`, run eval from the repo root. Eval uses a separate image (`Dockerfile.eval` on `vllm/vllm-openai:v0.26.0`) and `HF_EVAL_IMAGE`. Training still uses `HF_JOB_IMAGE` and `Dockerfile`. The eval job runs on `l4x1` ($0.80/hour) with an 8-hour timeout. Pass `--flavor a100-large` only after an L4 out-of-memory smoke.

Smoke 32 rows first (checks LoRA targets load and generations parse as `keep` / `remove` with thinking off):

```bash
HF_EVAL_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04-eval:latest \
    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/evaluate.py \
    --ablation unanimous \
    --limit 32
```

Full pass (one adapter, one pass over the 20,000-row table):

```bash
HF_EVAL_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04-eval:latest \
    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/evaluate.py \
    --ablation unanimous
```

Optional `--run-name` selects the adapter folder; otherwise the latest run under that ablation is used. The job downloads the adapter from S3, rewrites LoRA keys locally for vLLM (S3 object unchanged), scores `STUDY_2_KEEP_REMOVE_LABELS` once with `enable_thinking=False`, then writes unanimous, split, and all metrics from that pass. It uploads:

- `s3://mirrorview-experimental-artifacts/experiments/lora_finetuning_study2_2026_10_04/results/{ablation}/{run_name}/preds.jsonl`
- `s3://mirrorview-experimental-artifacts/experiments/lora_finetuning_study2_2026_10_04/results/{ablation}/{run_name}/metrics.jsonl`

When the job finishes, the launcher downloads metrics locally to:

`experiments/lora_finetuning_study2_2026_10_04/results/{ablation}/{run_name}/metrics.jsonl`

Expected L4 wall clock for the full table is about 1.5–3 hours ($1.20–$2.40). Conservative band is 4–7 hours ($3.20–$5.60). The 8-hour timeout caps spend at $6.40.
