# Step 2: Freeze balanced CSV splits and chat JSONL locally

## Goal

Materialize reproducible local training artifacts under `experiments/finetune_qwen_model_2026_08_08/data/`: balanced keep/remove CSVs and labeled chat JSONL for train and test. Vendor the rubric prompt into this experiment (edited closing line). Do **not** train or call SageMaker.

## Caller / unit of work

**Main caller:** CLI that builds splits then chat files.

Recommended entrypoints (either one orchestrator or two scripts invoked in order):

1. `PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/build_splits.py`
2. `PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py`

Or a single wrapper that calls both. Prefer two scripts matching the README filenames.

**Happy path:**

1. Load `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` via `shared.data.dataloader.load_dataset` (or `resolve_path` + pandas).
2. Keep **all** remove rows; sample **exactly** `len(removes)` keep rows with `random_state=1` (uniform without replacement).
3. Within the balanced 308-row frame, stratified 80/20 split by `decision` with `seed=1` so train and test each have equal keep and remove counts.
4. Write `data/train.csv` and `data/test.csv`.
5. For each split row, build chat record and write `data/chat_train.jsonl` / `data/chat_test.jsonl`.

**Out of scope:** training, inference, S3 upload, Docker, editing shared registry/transform CSVs, importing prompt-engineering packages (vendor text only).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/registry.py` | Registry name `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv` | Column schema / counts |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | Rubric template text to vendor |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py` | Prompt fill pattern to mirror in vendored code |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py` | Per-class `sample(..., random_state=...)` precedent |
| `/workspace/docs/plans/2026-08-08_finetune_qwen3_4b_lora_4403cd/plan.md` | Approved data contracts |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` (vendored template + system string + generate helper)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/train.csv` (generated)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/test.csv` (generated)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl` (generated)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/chat_test.jsonl` (generated)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (commands for these scripts only, if needed)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/` (optional unit tests for split math / prompt closing line)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**` (read-only vendor source)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` (no train logic this step)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py`
- Do not `git commit` unless asked

## Contracts to freeze

### Split math

| Constant | Value |
|----------|-------|
| Seed | `1` |
| Removes kept | all (`154` on current data) |
| Keeps sampled | equal to number of removes |
| Total balanced | `2 * n_remove` (`308` on current data) |
| Train fraction | `0.8` |
| Test fraction | `0.20` |
| Per-split balance | train keep count == train remove count; test keep == test remove |

Implementation rule for 80/20 with even class counts: for each class of size `n_class` in the balanced pool, put `int(0.8 * n_class)` in train and the remainder in test (for `n_class=154`, train 123 / test 31 per class → train 246 / test 62). If floating math would unbalance, fix by integer split per class, not global shuffle then cut.

Refuse to overwrite existing outputs unless `--force`.

### CSV columns

Must include at least: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`. Preserve `n_raters` if present in the source.

### Prompt / chat

| Piece | Contract |
|-------|----------|
| System content | Short fixed string: answer with exactly `keep` or `remove` (content-moderation assistant) |
| User content | Vendored study rubric template; Post 1 = `original_text`; Post 2 = `mirror_text`; closing line asks for `keep` or `remove` only (not “Allow Or Remove?”) |
| Assistant content | Exact gold `decision` string: `keep` or `remove` |
| JSONL line | `{"message_id": "<id>", "messages": [{"role":"system",...},{"role":"user",...},{"role":"assistant",...}]}` |
| Import rule | **No** import from `experiments.llm_prompt_engineering_*`; copy template text into `src/prompt.py` |

### Cross-experiment import ban

`src/prompt.py` and chat builders must not import `experiments.llm_prompt_engineering_2026_08_05` or `..._v2_...`.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force

PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
import pandas as pd

root = Path('experiments/finetune_qwen_model_2026_08_08/data')
train = pd.read_csv(root / 'train.csv')
test = pd.read_csv(root / 'test.csv')
assert len(train) + len(test) == 308, (len(train), len(test))
assert len(train) == 246 and len(test) == 62, (len(train), len(test))
for name, df in [('train', train), ('test', test)]:
    dec = df['decision'].astype(str).str.lower().str.strip()
    assert (dec == 'keep').sum() == (dec == 'remove').sum(), name
    assert df['message_id'].is_unique

# reproducibility: rebuild and compare message_id sets
ids1 = set(train['message_id'].astype(str)) | set(test['message_id'].astype(str))

def load_jsonl(p):
    rows = [json.loads(l) for l in Path(p).read_text(encoding='utf-8').splitlines() if l.strip()]
    return rows

for split, n in [('chat_train.jsonl', 246), ('chat_test.jsonl', 62)]:
    rows = load_jsonl(root / split)
    assert len(rows) == n, (split, len(rows))
    for r in rows:
        assert 'message_id' in r and 'messages' in r
        roles = [m['role'] for m in r['messages']]
        assert roles == ['system', 'user', 'assistant'], roles
        assert r['messages'][-1]['content'] in {'keep', 'remove'}
        assert 'Allow Or Remove?' not in r['messages'][1]['content']
print('step2 data OK')
"
```

Re-run both scripts with `--force` and assert `message_id` sets for train/test are identical to the first run.

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Counts | 308 total; 246/62; balanced classes | Any other split sizes |
| Seed | Identical IDs on `--force` rebuild | Non-deterministic sample |
| Chat schema | `message_id` + 3-role messages | Missing fields / wrong roles |
| Closing line | Asks keep/remove; no Allow Or Remove | Old study closing |
| Vendor | No prompt-eng package imports | Cross-experiment import |
| Shared data | Unchanged | Diff under `shared/` |

## Done when

1. Four data files exist under `experiments/finetune_qwen_model_2026_08_08/data/`.
2. Split and chat contracts above hold under automated asserts.
3. Prompt is vendored with keep/remove closing line.
4. No training or remote jobs.
