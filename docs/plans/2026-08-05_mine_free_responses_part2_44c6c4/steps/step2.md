# Step 2: Scaffold Part 2 package, low/high loader, and output layout

## Goal

Create `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/` with four stage-module stubs, a paths/loader for low/high reflection corpora, and documented output directory helpers. Load from `STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK`. Do **not** implement LLM, Bedrock, or clustering logic in this step. Do **not** edit the parent experiment README.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python -c "
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import paths
df = paths.load_reflection_feedback()
low_df, high_df = paths.split_by_likert_group(df)
print(len(df), len(low_df), len(high_df))
print(paths.stage1_root('low'))
print(paths.stage1_root('high'))
"
```

Expected approximate counts: total ~1177, low ~255, high ~922 (exact may vary slightly if CSV regenerated; assert `len(low_df) + len(high_df) == len(df)` after dropna on rating).

**In scope:** package stubs + paths/loader only.

**Out of scope:** live LLM/Bedrock; Stage-1 prompts; `RESULTS.md`; parent README edits; Part 1 histogram; keep/remove experiment; `shared/data/` changes.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md` | Part 2 layout, low/high split, output trees (read only — do not edit) |
| `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_1_histogram/plot.py` | Loader pattern for `STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK` |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Registry constant |
| `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/study_phase_2_part_2/README.md` | Columns: `participant_id`, `prolific_id`, `phase1_pair_reflection_text`, `phase1_pair_influence_rating` |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/paths.py` | Shape for stage roots + enum + `latest_timestamp_subdir` (prefer calling shared paths helper from Step 1 for timestamp utilities) |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-05_mine_free_responses_part2_44c6c4/plan.md` | Locked decisions |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/__init__.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/paths.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py` (create stub)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_embeddings.py` (create stub)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py` (create stub)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/generate_labels_for_embeddings.py` (create stub)
- Optional `.gitkeep` under `part_2_mine_free_responses/outputs/{generated_features,generated_embeddings,clusters,generated_labels}/{low,high}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_1_histogram/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- Do **not** create `RESULTS.md` in this step
- Do **not** create a Part-2 `tests/` package in this step

## Contracts to freeze

### Experiment root

```text
PART2_ROOT = experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/
```

### Likert groups

| Group | Rule |
|-------|------|
| `low` | `phase1_pair_influence_rating < 4` |
| `high` | `phase1_pair_influence_rating >= 4` |

- Require non-null numeric rating and non-empty `phase1_pair_reflection_text` (same usability spirit as the transform README).
- `LikertGroup` enum / validator: exactly `low` | `high`.

### Required columns after load

`participant_id`, `phase1_pair_reflection_text`, `phase1_pair_influence_rating` (keep `prolific_id` if present; not required for pipeline).

### Stage roots

| Helper | Path |
|--------|------|
| `stage1_root(group)` | `{PART2_ROOT}/outputs/generated_features/{low\|high}/` |
| `stage2_root(group)` | `{PART2_ROOT}/outputs/generated_embeddings/{low\|high}/` |
| `stage3_root(group)` | `{PART2_ROOT}/outputs/clusters/{low\|high}/` |
| `stage4_root(group)` | `{PART2_ROOT}/outputs/generated_labels/{low\|high}/` |

### Stage stubs

Each of the four stage modules must define `main` (or be importable) and raise `NotImplementedError` from the body until later steps. Docstrings may list the intended CLI from the parent README Part 2 section.

## Exact commands

### Pass

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import paths
df = paths.load_reflection_feedback()
low_df, high_df = paths.split_by_likert_group(df)
assert len(low_df) + len(high_df) == len(df)
assert (low_df['phase1_pair_influence_rating'] < 4).all()
assert (high_df['phase1_pair_influence_rating'] >= 4).all()
assert paths.stage1_root('low').name == 'low'
assert paths.stage1_root('high').name == 'high'
print(len(df), len(low_df), len(high_df))
print('step2 scaffold OK')
"
```

Expected: prints counts then `step2 scaffold OK`.

### Fail criteria

- Parent README modified
- Loader uses keep/remove labels dataset instead of user reflection feedback
- Mixed low+high without a split helper
- Real LLM/Bedrock logic in stubs

## Done when

1. Part 2 `src/` package and four stubs exist.
2. Loader + low/high split pass the offline check with expected count relationship.
3. Stage root helpers resolve under `part_2_mine_free_responses/outputs/`.
4. Parent README unchanged.
