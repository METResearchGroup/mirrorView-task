# Step 2: Freeze balanced modal-label CSV splits and chat JSONL

## Goal

Materialize reproducible local training artifacts under `experiments/finetune_qwen_model_modal_labels_2026_08_09/data/` from the **modal** keep/remove registry, using the **same balance and split helpers** as the prior experiment. Build chat JSONL by importing the prior prompt/chat helpers (do not re-vendor rubric text).

Do **not** train or call SageMaker.

## Caller / unit of work

**Main caller:** CLI that builds splits then chat files.

```bash
PYTHONPATH=. uv run python experiments/finetune_qwen_model_modal_labels_2026_08_09/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/finetune_qwen_model_modal_labels_2026_08_09/src/create_chat_dataset.py --force
```

**Happy path:**

1. Load `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset`.
2. Call `balance_keep_remove` and `stratified_balanced_split` imported from `experiments.finetune_qwen_model_2026_08_08.src.build_splits` with `seed=1` and `train_fraction=0.8`.
3. Write `data/train.csv` and `data/test.csv` under the **new** experiment root.
4. Build chat JSONL by importing `row_to_chat_record` (and/or prompt helpers) from the prior experiment; write `data/chat_train.jsonl` / `data/chat_test.jsonl`.

**Out of scope:** training, inference, S3 upload, Docker, editing shared registry CSVs, copying prompt template text into the new tree.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv` | Schema / counts (~8791; ~2813 remove) |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` | `balance_keep_remove`, `stratified_balanced_split`, validation helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` | `row_to_chat_record` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` | Prompt helpers to import |
| `/workspace/docs/plans/2026-08-09_finetune_qwen_modal_labels_5b07da/plan.md` | Data contracts |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/src/build_splits.py`
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/src/create_chat_dataset.py`
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/data/train.csv` (generated)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/data/test.csv` (generated)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/data/chat_train.jsonl` (generated)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/data/chat_test.jsonl` (generated)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/README.md` (commands only, if needed)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/tests/` (optional: assert registry + import wiring + counts)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` **only if** a pure helper must be extracted to accept an already-loaded frame / output dir without hardcoding the unanimous registry — keep the prior CLI behavior identical

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` (import only; do not edit)
- `/workspace/experiments/llm_prompt_engineering_*/**`
- New `src/prompt.py` that re-copies rubric text (forbidden — import prior)

## Contracts to freeze

### Split math (current modal data)

| Constant | Value |
|----------|-------|
| Registry | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| Seed | `1` |
| Removes kept | all (`2813` on current CSV) |
| Keeps sampled | equal to number of removes (`2813`) |
| Total balanced | `5626` |
| Train fraction | `0.8` per class → `int(0.8 * 2813) = 2250` per class |
| Train / test sizes | `4500` / `1126` |
| Per-split balance | train keep == train remove; test keep == test remove |

Refuse to overwrite existing outputs unless `--force`.

If the live CSV counts differ slightly from 2813, derive sizes from `n_remove` at runtime (still 1:1 and 80/20 integer-per-class); update README expected counts to match the freeze that was actually written.

### CSV columns

Must include at least: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`.

### Chat schema

Same as prior experiment:

| Piece | Contract |
|-------|----------|
| JSONL line | `{"message_id": "...", "messages": [system, user, assistant]}` |
| Assistant | Exact gold `decision`: `keep` or `remove` |
| Closing line | keep/remove only; no `Allow Or Remove?` |
| Import rule | Import prompt/chat helpers from `experiments.finetune_qwen_model_2026_08_08`; **no** new vendored copy |

### DRY gate

`rg -n "Allow Or Remove|You are a content moderation" experiments/finetune_qwen_model_modal_labels_2026_08_09` must find **no** rubric body (only possible references in README pointing at the prior package).

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/finetune_qwen_model_modal_labels_2026_08_09/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/finetune_qwen_model_modal_labels_2026_08_09/src/create_chat_dataset.py --force

PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
import pandas as pd
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

src = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)
dec = src['decision'].astype(str).str.lower().str.strip()
n_remove = int((dec == 'remove').sum())
n_train_per = int(0.8 * n_remove)
n_test_per = n_remove - n_train_per
expected_train = 2 * n_train_per
expected_test = 2 * n_test_per
expected_total = 2 * n_remove

root = Path('experiments/finetune_qwen_model_modal_labels_2026_08_09/data')
train = pd.read_csv(root / 'train.csv')
test = pd.read_csv(root / 'test.csv')
assert len(train) + len(test) == expected_total, (len(train), len(test), expected_total)
assert len(train) == expected_train and len(test) == expected_test, (len(train), len(test))
for name, df in [('train', train), ('test', test)]:
    d = df['decision'].astype(str).str.lower().str.strip()
    assert (d == 'keep').sum() == (d == 'remove').sum(), name
    assert df['message_id'].is_unique

def load_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding='utf-8').splitlines() if l.strip()]

for split, n in [('chat_train.jsonl', expected_train), ('chat_test.jsonl', expected_test)]:
    rows = load_jsonl(root / split)
    assert len(rows) == n, (split, len(rows), n)
    for r in rows:
        roles = [m['role'] for m in r['messages']]
        assert roles == ['system', 'user', 'assistant']
        assert r['messages'][-1]['content'] in {'keep', 'remove'}
        assert 'Allow Or Remove?' not in r['messages'][1]['content']
print('step2 data OK', expected_total, expected_train, expected_test)
"

# Reproducibility
PYTHONPATH=. uv run python experiments/finetune_qwen_model_modal_labels_2026_08_09/src/build_splits.py --force
PYTHONPATH=. uv run python -c "
import pandas as pd
from pathlib import Path
root = Path('experiments/finetune_qwen_model_modal_labels_2026_08_09/data')
# second freeze must match first; compare against files just rewritten is tautological —
# instead assert seed path: rebuild twice in-process via importing balance helpers.
from experiments.finetune_qwen_model_2026_08_08.src.build_splits import (
    balance_keep_remove,
    stratified_balanced_split,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS
src = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)
b1 = balance_keep_remove(src, seed=1)
b2 = balance_keep_remove(src, seed=1)
assert list(b1['message_id']) == list(b2['message_id'])
tr1, te1 = stratified_balanced_split(b1, 0.8, 1)
tr2, te2 = stratified_balanced_split(b2, 0.8, 1)
assert list(tr1['message_id']) == list(tr2['message_id'])
assert list(te1['message_id']) == list(te2['message_id'])
disk_tr = set(pd.read_csv(root/'train.csv')['message_id'].astype(str))
assert disk_tr == set(tr1['message_id'].astype(str))
print('step2 reproducibility OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Source | Modal registry, not unanimous | Wrong dataset |
| Counts | `2 * n_remove` total; 80/20 per class; balanced | Any other sizes |
| Seed | Identical IDs on rebuild | Non-deterministic sample |
| Chat | Prior helpers; schema matches PR #54 | Local re-vendored prompt |
| Shared / prior data | Unchanged | Diff under `shared/` or prior `data/` |

## Done when

1. Four data files exist under the new experiment `data/` directory.
2. Split/chat contracts hold under the asserts above.
3. Balance/split/prompt logic is imported from the prior experiment.
4. No training or remote jobs.
