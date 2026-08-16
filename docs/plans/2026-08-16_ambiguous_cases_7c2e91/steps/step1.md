# Step 1: Build the shared trial and post analysis frame

## Goal

Load Phase 2 Part 2 results, keep linked-fate keep or remove trials, and write one trial-level table and one post-level table that later steps read. Include exact ties. Do not drop posts with fewer than three raters from the trial table. The post table used for ambiguity scoring keeps posts with three or more raters and includes ties.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/build_analysis_frame.py
```

Flow: load `STUDY_PHASE_2_PART_2_RESULTS_FULL`, filter linked-fate keep or remove trials with a usable post id, write trial rows, aggregate post rows for posts with three or more raters including ties, join stimuli toxicity and stance, print counts.

In scope: builder module, trial CSV, post CSV.

Out of scope: scoring models, response-time models, RESULTS rewrite.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | Design contract |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` | Slim trial filter precedent |
| `/workspace/shared/data/registry.py` | Registry names |
| `/workspace/docs/plans/2026-08-16_ambiguous_cases_7c2e91/plan.md` | Executive summary |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/__init__.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/src/build_analysis_frame.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/post_frame.csv`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/**`
- `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md`

## Contracts to freeze

### Slim trial gate

Keep a row when all hold:

1. `evaluation_mode` equals `linked_fate` after lowercasing and stripping.
2. `decision` is `keep` or `remove` after lowercasing and stripping.
3. `post_id` is non-null, non-empty after stripping, and not the literal string `nan`.
4. `participant_id` is non-null and non-empty after stripping.

### Trial frame columns

Path: `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv`

| Column | Meaning |
|--------|---------|
| `participant_id` | rater id |
| `post_id` | message id |
| `decision` | `keep` or `remove` |
| `is_remove` | 1 if remove else 0 |
| `response_time_ms` | float response time |
| `trial_index` | session trial index |
| `party_group` | rater party from the trial row |
| `original_text` | original post text |
| `mirror_text` | mirror text |
| `char_count` | character length of original text |

Expected row count on current data: 24738.

### Post frame columns

Path: `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/frames/post_frame.csv`

Universe: posts with `n_raters >= 3`, including exact ties.

| Column | Meaning |
|--------|---------|
| `post_id` | message id |
| `n_raters` | integer at least 3 |
| `keep_count` | integer |
| `remove_count` | integer |
| `remove_share` | `remove_count / n_raters` |
| `is_unanimous` | true when one distinct decision |
| `is_tie` | true when `keep_count == remove_count` |
| `minority_share` | `min(keep_count, remove_count) / n_raters` |
| `vote_entropy` | binary entropy of remove share, 0 when unanimous |
| `sample_toxicity_type` | stimuli stratum |
| `sampled_stance` | `left` or `right` |
| `original_text` | original text |
| `mirror_text` | mirror text |

Expected on current data: 3993 posts, of which 275 ties.

### Public API

| Symbol | Role |
|--------|------|
| `TRIAL_FRAME_CSV` | path constant |
| `POST_FRAME_CSV` | path constant |
| `build_trial_frame(raw=None) -> DataFrame` | pure build |
| `build_post_frame(trial_frame, stimuli=None) -> DataFrame` | pure build |
| `write_analysis_frames() -> tuple[DataFrame, DataFrame]` | write both CSVs |

## Exact commands

### 1. Write frames and print counts

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/build_analysis_frame.py
```

Expected stdout includes:

```text
trial_rows 24738
post_rows_ge3 3993
tie_rows 275
```

### 2. Confirm CSV shapes

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd
trials = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/frames/trial_frame.csv")
posts = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/frames/post_frame.csv")
assert len(trials) == 24738
assert len(posts) == 3993
assert int(posts["is_tie"].sum()) == 275
assert posts["n_raters"].min() >= 3
print("frame_ok", len(trials), len(posts), int(posts["is_tie"].sum()))
PY
```

Expected:

```text
frame_ok 24738 3993 275
```

## Pass / fail

Pass: counts match, both CSVs exist with frozen columns, ties are present.

Fail: ties dropped, trial count drifts without plan revision, stimuli join silently drops posts.

## Commit gate

Commit the builder and both frame CSVs after the count command matches.
