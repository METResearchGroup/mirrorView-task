# Step 3: Run Analysis 2 Stage 1 features and word clouds

## Goal

Give every four cell post a Stage 1 feature set by reusing prior `create_llm_features` rows where possible and generating only missing posts. Then build four word clouds and top token tables with the locked token counting rules.

## Caller / unit of work

Main callers, in order:

```text
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py
```

Feature flow: load the cohort, load prior Stage 1 JSON feature rows from `experiments/create_llm_features_2026_08_05/`, keep reused rows whose `message_id` is in the cohort, find missing ids, run Stage 1 generation for missing ids only with the dual text prompt, write a merged feature table under this experiment, and refuse to write into the old experiment outputs tree.

Word cloud flow: load the merged feature table, split `feature_value` strings into tokens, drop stopwords and meta tokens, count each token at most once per post inside each cell, write top 30 token tables and four cloud images.

In scope: adapters and outputs under this experiment only.

Out of scope: Stages 2 through 4 of `create_llm_features`, edits to committed files under that experiment's `outputs/`, Analysis 1 or 3, README or RESULTS rewrites.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` | Stage 1 runner, batching, dual text prompt wiring |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/paths.py` | Stage 1 roots and keep or remove post loader |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/prompts.py` | Dual text feature prompt |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/schemas.py` | `feature_name`, `feature_value`, `category` |
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` | Bag of words rules |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/steps/step1.md` | Cohort contract |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/src/bow_tokens.py` (create, optional helper)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/merged_stage1_features.jsonl` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/coverage.json` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/top_tokens_by_cell.csv` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/wordcloud_unanimous_keep.png` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/wordcloud_majority_keep.png` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/wordcloud_majority_remove.png` (create or regenerate)
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/wordcloud_unanimous_remove.png` (create or regenerate)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/outputs/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/**` (import and call only; do not patch unless a tiny read only import forces a follow up plan revision)
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/**` (read only)

## Contracts to freeze

### Prior Stage 1 sources (read only)

Load feature rows from both class trees:

- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/outputs/generated_features/remove/outputs/`

For each class, use the newest run directory that contains batch JSON files. Parse each batch file's `result.features` list. Keep fields `message_id`, `feature_name`, `feature_value`, `category`, `is_open_ended`, `evidence_span`, `rationale`.

If the same `message_id` appears in more than one prior run, keep the newest run's features for that id and record the choice in `coverage.json`.

### Reuse and generate

Let `C` be the set of cohort `message_id` values.

- Reused set: prior Stage 1 `message_id` values that fall in `C`
- Missing set: `C` minus the reused set

Generate Stage 1 features only for the missing set. Reuse prompts, schema, model default `gpt-5.4-nano`, and dual text post payload shape from `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` and `prompts.py`.

Batch missing posts without dropping a remainder. If the final batch is smaller than the default posts per batch size, still send it.

New generation writes only under `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/`.

### Coverage artifact

Path: `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/coverage.json`

Required keys:

- `cohort_n`
- `reused_n`
- `generated_n`
- `missing_after_run_n` must equal 0 when the feature script finishes
- `reused_message_ids` or a count plus a path to an id list is acceptable if the JSON would be huge; if ids are omitted, write `reused_n` and `generated_n` and a separate `missing_message_ids.txt` that is empty at success

### Merged features

Path: `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/merged_stage1_features.jsonl`

One JSON object per feature row, including `message_id`, `feature_value`, `category`, and `cell` joined from the cohort.

Every cohort `message_id` must appear at least once after a successful feature run. A post may have multiple feature rows.

### Token counting rules

For each cell:

1. Collect that cell's feature rows.
2. For each `message_id`, build the set of tokens found in any of that post's `feature_value` strings.
3. Lowercase the text, split on non letter characters, and drop empty tokens.
4. Drop English stopwords, single character tokens, and the low content tokens `none`, `in`, `or`, `and`, `the`, `a`, `an`, `of`, `to`, `for`, `with`, `on`, `at`, `by`, `from`.
5. Drop meta tokens `mirror`, `original`, `mirrors`, `mirrored`.
6. Count how many posts in the cell contain each remaining token.
7. Write the top 30 tokens by that count for the cell.

### Word cloud and table outputs

`top_tokens_by_cell.csv` columns: `cell`, `token`, `n_posts`, `rank`.

One PNG word cloud per cell at the paths listed in Files allowed to change. Word size in each cloud follows `n_posts`.

## Exact commands

### 1. Coverage probe before generation

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd

cohort = pd.read_csv(
    "experiments/unanimous_vs_majority_labels_2026_08_08/outputs/cohort/four_cell_cohort.csv"
)
cohort_ids = set(cohort["message_id"].astype(str))
prior_ids = set()
root = Path("experiments/create_llm_features_2026_08_05/outputs/generated_features")
for label in ("keep", "remove"):
    runs = sorted((root / label / "outputs").glob("*"))
    if not runs:
        continue
    run = runs[-1]
    for path in run.glob("*.json"):
        if path.name == "metadata.json":
            continue
        data = json.loads(path.read_text())
        for feat in data.get("result", {}).get("features", []):
            prior_ids.add(str(feat["message_id"]))
overlap = cohort_ids & prior_ids
print({"cohort_n": len(cohort_ids), "prior_overlap_n": len(overlap), "missing_n": len(cohort_ids - prior_ids)})
PY
```

Expected: `cohort_n` is 3718, `prior_overlap_n` is greater than 0 and far less than 3718, and `missing_n` is positive.

### 2. Generate and merge features

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_features.py
```

Expected: `coverage.json` has `missing_after_run_n` equal to 0, and `merged_stage1_features.jsonl` exists.

### 3. Build word clouds and top tokens

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis2_wordclouds.py
```

Expected: four PNG files exist, and `top_tokens_by_cell.csv` has 120 rows when every cell yields 30 tokens, or fewer only if a cell has fewer than 30 distinct tokens after scrubbing.

### 4. Top token shape check

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
from pathlib import Path
tokens = pd.read_csv(
    "experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/top_tokens_by_cell.csv"
)
assert {"cell", "token", "n_posts", "rank"} <= set(tokens.columns)
for cell in [
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
]:
    assert (Path("experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2") / f"wordcloud_{cell}.png").exists()
banned = {"none", "mirror", "original", "the", "and"}
assert tokens["token"].str.lower().isin(banned).sum() == 0
print("analysis2_ok", tokens.groupby("cell").size().to_dict())
PY
```

Expected stdout starts with `analysis2_ok`.

## Pass / fail

Pass:

- Every cohort post has at least one merged Stage 1 feature row.
- Output files under `experiments/create_llm_features_2026_08_05/` are unchanged.
- Top tokens count each token at most once per post and exclude the banned meta and stop tokens.
- Four word cloud PNGs exist.

Fail:

- Feature script writes under `experiments/create_llm_features_2026_08_05/outputs/`.
- Remainder posts are skipped because a batch was not full.
- Token counts treat whole `feature_value` strings as single tokens instead of splitting them into words.

## Commit gate

Commit Analysis 2 scripts and outputs after the shape check passes. Do not commit changes under `experiments/create_llm_features_2026_08_05/`.
