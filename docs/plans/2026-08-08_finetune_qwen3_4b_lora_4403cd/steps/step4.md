# Step 4: Implement inference entrypoint (baseline and adapter)

## Goal

Implement `experiments/finetune_qwen_model_2026_08_08/inference.py` to run greedy keep/remove generation over chat JSONL for (a) base model only and (b) base + LoRA adapter, writing prediction CSVs with the frozen schema.

## Caller / unit of work

**Main caller:** `inference.py` CLI (also SageMaker modes `infer_baseline` / `infer_adapter`).

```text
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-csv /tmp/train_labels.csv \
  --mode baseline

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_test.jsonl \
  --output-csv /tmp/test_labels.csv \
  --mode adapter \
  --adapter-dir /path/to/adapter
```

Happy path per row:

1. Read `message_id` + `messages`; use **system + user only** for generation (ignore assistant content except as gold).
2. Gold `decision` = assistant content; gold `keep_remove_label` = `1` if remove else `0`.
3. Generate greedily (`do_sample=False`); `max_new_tokens` in `{4,5,6,7,8}`.
4. Parse case-insensitive first whitespace-delimited token; accept only `keep` / `remove`.
5. On failure: `predicted_decision=__invalid__`, `predicted_label` empty/NA; log `raw_generation`.
6. Write CSV rows for all inputs.

`--mode baseline` must not load an adapter. `--mode adapter` requires `--adapter-dir` and fails if missing.

Fail fast if `HF_TOKEN` missing.

**Out of scope:** training; metrics aggregation; SageMaker submit; modifying chat JSONL.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl` | Input schema from Step 2 |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` | Shared `MODEL_ID` / tokenizer conventions |
| `/workspace/docs/plans/2026-08-08_finetune_qwen3_4b_lora_4403cd/plan.md` | Pred schema + invalid rule |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/` parse helpers if extracted
- `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/test_parse_prediction.py` (no GPU required)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (infer CLI docs)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_*/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` (Step 5)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` (Step 7)

## Contracts to freeze

### Output CSV columns (exact order preferred)

1. `message_id`
2. `decision` (gold)
3. `keep_remove_label` (gold int 0/1)
4. `raw_generation`
5. `predicted_decision` (`keep` | `remove` | `__invalid__`)
6. `predicted_label` (int 0/1, or empty/NA when invalid)

### Parse rules

| Input generation | `predicted_decision` | `predicted_label` |
|------------------|----------------------|-------------------|
| `keep` / `Keep` / `keep\n...` (first token keep) | `keep` | `0` |
| `remove` / `Remove` | `remove` | `1` |
| `allow`, `yes`, empty, multi-word without leading keep/remove | `__invalid__` | NA/empty |

### Modes

| Mode | Adapter |
|------|---------|
| `baseline` | none |
| `adapter` | required directory with PEFT adapter files |

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/finetune_qwen_model_2026_08_08/tests/test_parse_prediction.py -q

# Dry structural check without GPU if implemented:
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/inference.py --help
```

Optional GPU smoke on 2 rows (not a hard gate without GPU): `--limit 2`.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Parser unit tests | keep/remove/invalid cases green | Wrong mapping |
| Baseline mode | rejects `--adapter-dir` requirement; does not load adapter | Loads adapter anyway |
| Adapter mode | errors if `--adapter-dir` missing | Silent baseline |
| CSV schema | six columns present | Missing columns |
| Gold sourcing | from assistant turn | Recomputed incorrectly from CSV-only without JSONL gold |

## Done when

1. `inference.py` supports baseline and adapter modes with frozen CSV schema.
2. Parser tests cover invalid → NA label.
3. No evaluate/RESULTS or launcher work claimed.
