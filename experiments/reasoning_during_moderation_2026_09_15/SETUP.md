# Setup

`cohort.py --write-counts` downloads Prolific CSVs from `s3://jspsych-mirror-view-2026-09-09/data/prolific/` dated on or after 2026-09-09, using helpers in `scripts.export_study_results`. It does not load the registered Phase 2 Part 2 CSV.

The live study bucket is read-only. Write derived files to `s3://mirrorview-experimental-artifacts/experiments/reasoning_during_moderation_2026_09_15/`.

The build drops worker-post pairs that contain both keep and remove, then keeps the earliest remaining row per worker and post. A post stays in if it still has at least four unique raters.

The three groups are:

- `split`, only for vote patterns 2 keep and 2 remove, 3 keep and 2 remove, or 2 keep and 3 remove
- `unanimous_keep`
- `unanimous_remove`

Posts that are not unanimous and not in those three split patterns are excluded.

For each post, seed 0 plus the post id picks whether original or mirror is labeled Post 1. The cohort stores that as `post_1_role` and `post_2_role`. Experiment 1 uses those roles. Experiment 2 copies them from experiment 1 traces when those files exist.

The 2026-09-15 snapshot floor is `csv_files=3075`, `split=2200`, `unanimous_keep=2256`, `unanimous_remove=208`, `eligible_posts=4664`. `--write-counts` fails if any group is empty or if `csv_files` is below 3075. `RESULTS.md` records the export that was actually summarized.

Build the cohort first. Experiments 1 through 4 read its parquet.

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
```

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q
```

After `HF_TOKEN` is set, run a thinking-mode smoke on Hugging Face Jobs with vLLM (`vllm/vllm-openai:v0.17.0`). Qwen thinking uses temperature 1.0, top_p 0.95, top_k 20, and presence_penalty 1.5. DeepSeek-R1-Distill uses temperature 0.6 and top_p 0.95. Smoke `max_new_tokens` is 2048. If a smoke post is truncated at 2048, rerun with `--max-new-tokens 8192`. Full runs use 8192. Completions go through batched `vllm.LLM.generate`. Full-run jsonl files land under `outputs/vllm/` so they do not mix with the earlier Transformers traces.

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
```

On a machine without a GPU, build the `hf jobs run` command with `hf_job_command` in `shared/jobs.py` and run that instead of `run.py` locally.

Experiment 1 writes one thinking-mode completion per cohort post per model and counts tokens inside the think span. Run one Hugging Face Job per model. `--summarize` can run locally after both jsonl files exist.

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --model qwen
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --model deepseek
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --summarize
```

Experiment 2 repeats experiment 1 with the keep/remove criteria addendum. Pair order and generation seeds match experiment 1 traces when those files exist.

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --model qwen
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --model deepseek
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --summarize
```

Experiment 3 summarizes finite `response_time_ms` values greater than zero on the slim trials. `trial` is one row per rating. `post_mean` averages those times per post, then writes the same stats by group. The summary does not read `rt`.

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
```

Experiment 4 flags uncertainty, revision, and tension phrases and tokens on stored thinking text, then writes `RESULTS.md`. It writes broad family rates, strict family rates with density, phrase-only rates, per-item rates, and split-minus-keep contrasts. Partial experiment 2 traces are ignored until both models have a full post set.

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
```
