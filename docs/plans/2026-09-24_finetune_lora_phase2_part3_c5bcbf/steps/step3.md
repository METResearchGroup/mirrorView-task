# Step 3: Add the SageMaker wrapper and run a smoke job

## Scope

- **Caller:** `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py` `main`, then `terraform apply`, Docker build/tag/push to ECR in `us-east-2`, `--dry-run`, and a live SageMaker smoke job (`--run-id part3_smoke_001`).
- **Task:** Add `E/shared/run_config.py`, `E/launch_sagemaker.py`, `E/Dockerfile`, and `E/entrypoint.sh` mirroring `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/`. Do not add `E/train.py` or `E/inference.py`; `E/entrypoint.sh` calls `P/train.py` and `P/inference.py` directly. Extend `P/train.py` and `P/inference.py` with optional CLI flags (defaults preserve Part 2). Add S3 prefix and ECR repo to `P/infra/main.tf`. Build and push the image, then smoke train (2 steps) and infer (5 rows per test set) on `Qwen/Qwen3.5-4B` with thinking disabled.
- **Out of scope:** Full experiment trains (Steps 4 to 7), `E/shared/build_splits.py`, `E/shared/create_chat_dataset.py`, `score_all.py`, adapters in git.

Notation: `E` = `/workspace/experiments/finetune_lora_phase2_part3_2026_09_24/`, `P` = `/workspace/experiments/finetune_qwen_model_2026_08_08/`, `W` = `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/`.

### Verified upstream facts

| Topic | Finding |
|-------|---------|
| Model class | `Qwen/Qwen3.5-4B` loads with `AutoModelForCausalLM.from_pretrained(..., trust_remote_code=True)` (same as `P/train.py`). Text-only SageMaker jobs do not need `AutoModelForImageTextToText`. |
| Transformers | `pyproject.toml` group `finetune-qwen-2026-08-08` requires `transformers>=5.8.1,<5.13` and `trl>=0.15.0,<1.10`; `uv.lock` resolves `transformers` `5.12.1` and `trl` `1.9.2`. Older Dockerfiles pin `>=4.49.0`. `E/Dockerfile` must pin `transformers>=5.8.1,<5.13` and `trl>=0.15.0,<1.10` because newer `trl` and `transformers` dropped `warmup_ratio` from the config August `P/train.py` builds. |
| Disable thinking | Pass `enable_thinking=False` to `tokenizer.apply_chat_template` (same as `chat_template_kwargs={"enable_thinking": False}` on the model card). An empty `<think></think>` block from the template is allowed; generated text must not include thinking content. |

## Dependencies

Step 2 synced data to `s3://mirrorview-experimental-artifacts/experiments/finetune_lora_phase2_part3_2026_09_24/`: shared `data/` (`split_manifest.csv`, test CSVs, `chat_test_unanimous.jsonl`, `chat_test_modal.jsonl`) and `experiment{1,2,3}_*/data/chat_train.jsonl`. Smoke train uses `experiment1_unanimous/data/`; smoke infer uses shared `data/` test chat files.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md` | Decisions and pool table; Step 3 scope and commands |
| `W/{launch_sagemaker.py,entrypoint.sh,Dockerfile}` | Wrapper to mirror |
| `P/{launch_sagemaker.py,entrypoint.sh,Dockerfile,train.py,inference.py,infra/main.tf}` | Prior launcher, container, train/infer, Terraform |
| `P/src/train_config.py` | LoRA hyperparam source for `dataclasses.replace` |
| `P/tests/test_launch_sagemaker_config.py` | Launcher test style |
| `/workspace/pyproject.toml`, `/workspace/uv.lock` | `finetune-qwen-2026-08-08` deps |
| `https://huggingface.co/Qwen/Qwen3.5-4B` | `enable_thinking=False` contract |

## Files allowed to change

- `E/shared/run_config.py`, `E/launch_sagemaker.py`, `E/Dockerfile`, `E/entrypoint.sh` (new)
- `E/tests/test_run_config.py`, `E/tests/test_launch_sagemaker_config.py` (new)
- `P/train.py`, `P/inference.py`, `P/infra/main.tf`

## Files forbidden to change

- `/workspace/shared/data/**`, `P/src/**`, `P/tests/**`, `W/**`
- `E/shared/build_splits.py`, `create_chat_dataset.py`, `README.md`, `SETUP.md`, `RESULTS.md` (Step 2)
- `/workspace/webapp/**`, `/workspace/tests/**`, `/workspace/CHANGELOG.md`

## Public contracts

### `E/shared/run_config.py`

`MODEL_ID="Qwen/Qwen3.5-4B"`, `CHAT_TEMPLATE_KWARGS={"enable_thinking": False}`, `S3_BUCKET="mirrorview-experimental-artifacts"`, `S3_PREFIX="experiments/finetune_lora_phase2_part3_2026_09_24"`, `ECR_REPO_NAME="mirrorview-finetune-lora-phase2-part3"`, `WANDB_PROJECT="mirrorview-finetune-lora-phase2-part3"`, `EXPERIMENT_EPOCHS={"experiment1_unanimous": 3, "experiment2_modal": 1, "experiment3_modal_size_matched": 3}`, `RANDOM_SEED=1`, `AWS_REGION="us-east-2"`, `INSTANCE_TYPE="ml.g5.xlarge"`. `default_hyperparams()` uses `dataclasses.replace` on `default_hyperparams()` in `P/src/train_config.py` for `model_id`, `seed`, `wandb_project`, and per-experiment `num_train_epochs`.

### `E/launch_sagemaker.py`

Wrapper over `P.launch_sagemaker.build_job_config` (same pattern as `W`). CLI exactly:

`--mode {train,infer_baseline,infer_adapter} --experiment {experiment1_unanimous,experiment2_modal,experiment3_modal_size_matched,experiment4_cross_eval} --run-id RUN_ID [--smoke] [--dry-run] [--wait]`

`--smoke`: train sets `max_steps=2`; infer sets `limit=5`. Reject `--mode train` with `--experiment experiment4_cross_eval`, `--mode infer_adapter` with `experiment4_cross_eval`, and `--mode infer_baseline` for experiments 1 to 3. Allow `--mode infer_baseline` only with `experiment4_cross_eval`.

S3 URIs (local path = S3 key under prefix):

| Mode | data channel | adapter channel | output_path |
|------|--------------|-----------------|-------------|
| train | `{prefix}/{experiment}/data/` | n/a | `{prefix}/{experiment}/adapters/{run_id}/` |
| infer_baseline | `{prefix}/data/` | n/a | `{prefix}/{experiment}/preds/` |
| infer_adapter | `{prefix}/data/` | `{prefix}/{experiment}/adapters/{run_id}/` | `{prefix}/{experiment}/preds/` |

Env keys: `HF_TOKEN`, `RUN_ID`, `MODE`, `AWS_REGION`, `MODEL_ID`, `CHAT_TEMPLATE_KWARGS_JSON`, `NUM_TRAIN_EPOCHS` (train), `WANDB_PROJECT` + `WANDB_API_KEY` (train), `ADAPTER_S3_URI` (train), `PREDS_S3_URI` (infer), `SMOKE=1` when `--smoke`. Role from `SAGEMAKER_ROLE_ARN` (terraform output `sagemaker_execution_role_arn`). Entry point: `/app/experiments/finetune_lora_phase2_part3_2026_09_24/entrypoint.sh`.

### `E/entrypoint.sh`

Modes `train | infer_baseline | infer_adapter`. `EXP_DIR=/app/experiments/finetune_lora_phase2_part3_2026_09_24`.

- **train:** `python P/train.py --train-jsonl ${SM_CHANNEL_DATA}/chat_train.jsonl --output-dir ${SM_MODEL_DIR}` with `--model-id`, `--num-train-epochs`, `--chat-template-kwargs-json` from env; add `--max-steps 2` when `SMOKE=1`.
- **infer_*:** two calls to `P/inference.py` on `chat_test_unanimous.jsonl` and `chat_test_modal.jsonl`, writing `test_unanimous.csv` and `test_modal.csv` under `${SM_MODEL_DIR}`. Pass `--chat-template-kwargs-json`; add `--limit 5` when `SMOKE=1`. Adapter mode uses `--adapter-dir ${SM_CHANNEL_ADAPTER}`.

Do not use `P/inference.py --both-splits` (scores train+test, wrong filenames).

### `P/train.py` and `P/inference.py`

Add optional CLI flags only (no `E/train.py` or `E/inference.py` wrappers). `P/train.py`: `--model-id`, `--num-train-epochs`, `--chat-template-kwargs-json` (JSON dict for `tokenizer.apply_chat_template`; omit or null keeps Part 2 behavior). `P/inference.py`: `--model-id`, `--chat-template-kwargs-json`. Part 2 tests must still show 20 passed.

### Template parity contract

Train and infer must render the same prompt with thinking disabled. `TestTemplateParity` in `E/tests/test_run_config.py` asserts the infer-rendered prompt does not match `re.search(r"<think>\\s*\\S", prompt)` (no non-whitespace thinking body). Only an empty `<think></think>` block is allowed.

### `E/Dockerfile` and `P/infra/main.tf`

`E/Dockerfile`: copy `shared/`, `lib/`, `P/`, `E/`; pin `transformers>=5.8.1,<5.13` and `trl>=0.15.0,<1.10` (newer `trl` and `transformers` dropped `warmup_ratio` from the config August `P/train.py` builds); entrypoint `E/entrypoint.sh`. `main.tf`: append `experiments/finetune_lora_phase2_part3_2026_09_24` to `local.s3_prefixes` and `mirrorview-finetune-lora-phase2-part3` to `local.ecr_repos`.

## Pytest files

Under `E/tests/`. No model download. Arrange-Act-Assert.

### `test_run_config.py`

Class `TestRunConfig`:

```text
given default_hyperparams for experiment1_unanimous
when compared to P defaults
then model_id is Qwen/Qwen3.5-4B, seed is 1, lora r is 16, num_train_epochs is 3

given experiment2_modal
when EXPERIMENT_EPOCHS lookup
then num_train_epochs is 1
```

Class `TestTemplateParity`:

```text
given enable_thinking false and one rubric chat record
when infer prompt is rendered
then no redacted_thinking block has non-whitespace content beyond the empty template block
```

### `test_launch_sagemaker_config.py`

Class `TestBuildJobConfig`:

```text
given train, experiment1_unanimous, run_id part3_smoke_001
when build_job_config
then data_s3_uri ends with experiment1_unanimous/data/
and output ends with experiment1_unanimous/adapters/part3_smoke_001/
and CHAT_TEMPLATE_KWARGS_JSON contains enable_thinking false

given infer_adapter, experiment1_unanimous, run_id part3_uni_001
when build_job_config
then adapter channel ends with adapters/part3_uni_001/
and output ends with experiment1_unanimous/preds/

given train and experiment4_cross_eval
when build_job_config
then raise ValueError

given infer_adapter and experiment4_cross_eval
when build_job_config
then raise ValueError

given infer_baseline and experiment1_unanimous
when build_job_config
then raise ValueError

given infer_baseline and experiment4_cross_eval
when build_job_config
then output ends with experiment4_cross_eval/preds/
```

## Main caller

Run from `/workspace` with AWS creds exported per `AGENTS.md`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
cd experiments/finetune_qwen_model_2026_08_08/infra && terraform init && terraform apply -auto-approve
export SAGEMAKER_ROLE_ARN="$(terraform output -raw sagemaker_execution_role_arn)"

cd /workspace
docker build -f experiments/finetune_lora_phase2_part3_2026_09_24/Dockerfile \
  -t mirrorview-finetune-lora-phase2-part3:latest .
# tag and push to <account>.dkr.ecr.us-east-2.amazonaws.com/mirrorview-finetune-lora-phase2-part3:latest

PYTHONPATH=. uv run pytest experiments/finetune_lora_phase2_part3_2026_09_24/tests -q
PYTHONPATH=. uv run pytest experiments/finetune_qwen_model_2026_08_08/tests -q
# Expected: Part 3 tests pass; prior package ends with 20 passed

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode train --experiment experiment1_unanimous --run-id part3_smoke_001 --smoke --dry-run
# Expected: prints job config, experiment1_unanimous/data URI, dry-run: not submitting fit()

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode train --experiment experiment1_unanimous --run-id part3_smoke_001 --smoke --wait
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \
  --mode infer_adapter --experiment experiment1_unanimous --run-id part3_smoke_001 --smoke --wait
```

Smoke result: train finishes 2 steps; infer writes 5 rows each to `test_unanimous.csv` and `test_modal.csv` on S3 under `experiment1_unanimous/preds/`; each `predicted_decision` is `keep` or `remove`.

## Must pass

- `E/tests` exit 0; `P/tests` print `20 passed`.
- Terraform adds prefix and ECR repo; `SAGEMAKER_ROLE_ARN` resolves.
- `E/Dockerfile` pins `transformers>=5.8.1,<5.13` and `trl>=0.15.0,<1.10` so SageMaker matches the capped stack August `P/train.py` expects (`warmup_ratio` on the training config).
- Dry-run prints experiment-scoped URIs and `enable_thinking` false.
- Smoke: 2 train steps, 5+5 valid predictions, template parity test green.

## Must fail

- Training on `chat_test_*.jsonl`; `train` with `experiment4_cross_eval`; `infer_adapter` with `experiment4_cross_eval`; `infer_baseline` with experiments 1 to 3.
- Omitting `enable_thinking=False` on Part 3 jobs.
- Using `--both-splits` for Part 3 infer.
- `transformers>=4.49.0` in `E/Dockerfile`; changing `P/tests`; adapters in git.

## Implement-from-spec notes

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md`. Full auto. Phase 1: `launch_sagemaker.py` caller. Phase 2: scaffold files. Phase 3: lock contracts (`chat_template_kwargs` default `None`, S3 table, entrypoint modes). Phase 4: pytest from given/when/then blocks. Phase 5: `run_config` and `TestTemplateParity`, then `P` kwargs, `launch_sagemaker`, `entrypoint` and `Dockerfile`, `main.tf`, docker push, live smoke. Phase 6: unit tests green, smoke done, `20 passed` on Part 2.
