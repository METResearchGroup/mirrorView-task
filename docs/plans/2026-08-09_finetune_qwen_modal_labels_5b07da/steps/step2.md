# Step 2: Freeze balanced modal-label CSV splits and chat JSONL

## Goal

Write reproducible local training files under `experiments/larger_finetune_qwen_model_2026_08_08/data/` from the modal keep/remove registry, using the same balance and split helpers as the earlier experiment. Build chat JSONL by importing the earlier prompt and chat helpers. Do not copy the rubric text into the new tree.

Do not train a model or call SageMaker in this step.

## Caller / unit of work

The main caller is a CLI that builds the splits and then the chat files.

```bash
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force
```

Happy path:

1. Load `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset`.
2. Call `balance_keep_remove` and `stratified_balanced_split` imported from `experiments.finetune_qwen_model_2026_08_08.src.build_splits` with `seed=1` and `train_fraction=0.8`.
3. Write `data/train.csv` and `data/test.csv` under the new experiment root.
4. Build chat JSONL by importing `row_to_chat_record` or the prompt helpers from the earlier experiment, and write `data/chat_train.jsonl` and `data/chat_test.jsonl`.

Work that is out of scope includes training, inference, S3 upload, Docker, editing shared registry CSVs, and copying prompt template text into the new tree.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv` | Schema and counts (about 8791 rows, about 2813 remove) |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` | `balance_keep_remove`, `stratified_balanced_split`, and validation helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` | `row_to_chat_record` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` | Prompt helpers to import |
| `/workspace/docs/plans/2026-08-09_finetune_qwen_modal_labels_5b07da/plan.md` | Data contracts |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/data/train.csv` (generated)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/data/test.csv` (generated)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl` (generated)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/data/chat_test.jsonl` (generated)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (commands only, if needed)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/tests/` (optional asserts for registry, import wiring, and counts)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` only if a pure helper must be extracted so it can take an already-loaded frame or output directory without hardcoding the unanimous registry. Keep the earlier CLI behavior the same.

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` (import only; do not edit)
- `/workspace/experiments/llm_prompt_engineering_*/**`
- A new `src/prompt.py` that recopies rubric text. Import the earlier prompt module instead.

## Contracts to freeze

### Split math (current modal data)

| Constant | Value |
|----------|-------|
| Registry | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| Seed | `1` |
| Removes kept | All (`2813` on the current CSV) |
| Keeps sampled | Equal to the number of removes (`2813`) |
| Total balanced | `5626` |
| Train fraction | `0.8` per class, so `int(0.8 * 2813) = 2250` per class |
| Train and test sizes | `4500` and `1126` |
| Per-split balance | Train keep count equals train remove count, and test keep count equals test remove count |

Refuse to overwrite existing outputs unless `--force` is passed.

If the live CSV counts differ slightly from 2813, derive sizes from `n_remove` at runtime while keeping equal classes and an integer 80/20 split per class. Update the README expected counts to match the freeze that was actually written.

### CSV columns

The CSV files must include at least `message_id`, `original_text`, `mirror_text`, `decision`, and `keep_remove_label`.

### Chat schema

Use the same chat shape as the earlier experiment.

| Piece | Contract |
|-------|----------|
| JSONL line | `{"message_id": "...", "messages": [system, user, assistant]}` |
| Assistant | Exact gold `decision` of `keep` or `remove` |
| Closing line | Asks for keep or remove only, and does not contain `Allow Or Remove?` |
| Import rule | Import prompt and chat helpers from `experiments.finetune_qwen_model_2026_08_08`. Do not add a new copy of the rubric text. |

### DRY gate

`rg -n "Allow Or Remove|You are a content moderation" experiments/larger_finetune_qwen_model_2026_08_08` must find no rubric body. The only allowed mention is a README note that points at the earlier package.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force

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

root = Path('experiments/larger_finetune_qwen_model_2026_08_08/data')
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
PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py --force
PYTHONPATH=. uv run python -c "
import pandas as pd
from pathlib import Path
root = Path('experiments/larger_finetune_qwen_model_2026_08_08/data')
# Rebuild twice in process with the shared helpers and compare message_id lists.
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
| Counts | `2 * n_remove` total, 80/20 per class, balanced classes | Any other sizes |
| Seed | Identical IDs on rebuild | Non-deterministic sample |
| Chat | Earlier helpers, schema matches pull request 54 | A local recopy of the prompt |
| Shared and earlier data | Unchanged | A diff under `shared/` or the earlier `data/` |

## Done when

1. Four data files exist under the new experiment `data/` directory.
2. The split and chat contracts hold under the asserts above.
3. Balance, split, and prompt logic is imported from the earlier experiment.
4. There is still no training and no remote job.
