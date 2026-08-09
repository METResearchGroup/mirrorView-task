# Step 1: Freeze filter contract, registry name, and output schema

## Goal

Lock the inclusion rule, output schema, registry identity, and acceptance counts for the new shared dataset before writing transform code. This step is documentation-only inside the plan packet (no production code changes yet). Implementers must treat the contracts below as frozen unless the plan is revised.

## Caller / unit of work

**Main caller (downstream):** `shared.data.dataloader.load_dataset(<NEW_REGISTRY_NAME>)` after Steps 2–3.

**In scope:** freeze contracts listed below; confirm measured counts against current `STUDY_PHASE_2_PART_2_RESULTS_FULL`.

**Out of scope:** writing the transform script, editing `registry.py`, regenerating CSVs, migrating experiments.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/registry.py` | Existing Part 2 transformed entry shape |
| `/workspace/shared/data/dataloader.py` | Loader API (`load_dataset`) |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | Linked-fate trial filter + modal aggregation precedent |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Transform documentation contract precedent |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | Frozen unanimous rule id/text (`all_linked_fate_raters_same_decision`) |
| `/workspace/docs/plans/2026-08-08_unanimous_min3_keep_remove_shared_dataset_e84ad2/plan.md` | Executive summary and out-of-scope |

## Files allowed to change

- None in the repo for this step (contract freeze only). If measured counts on current raw data diverge from the numbers below by more than 0, stop and revise this plan before Step 2.

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/**`
- `/workspace/scripts/**`
- Existing modal labels CSV and registry entry

## Contracts to freeze

### Registry identity

| Field | Frozen value |
|-------|----------------|
| Registry name | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` |
| Relative path | `shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv` |
| Kind | `transformed` |
| Study phase | `study_phase_2_part_2` |
| Transform module | `shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` |

### Inclusion rule (must hold for every output row)

Start from `STUDY_PHASE_2_PART_2_RESULTS_FULL` rows that pass the same slim-trial gate as `transform.py`:

1. `evaluation_mode == "linked_fate"` (case-insensitive after strip).
2. `decision ∈ {keep, remove}` (case-insensitive after strip).
3. Non-null, non-empty `post_id` after strip; drop literal `"nan"`.

Then aggregate per `post_id`:

4. `n_raters` = number of slim-trial rows for that post.
5. `is_unanimous` = True iff `nunique(decision) == 1` (same meaning as BERTopic `UNANIMOUS_RULE_ID = "all_linked_fate_raters_same_decision"`).
6. Keep the post only if `n_raters >= 3` **and** `is_unanimous` is True.

**Label assignment:** because the post is unanimous, `decision` is that single shared label (`keep` or `remove`). Set `keep_remove_label` to `1` for remove and `0` for keep (same encoding as modal labels). Do **not** apply the modal tie→remove rule (ties cannot appear in this subset).

**Text stability:** assert each kept `post_id` has exactly one distinct `original_text` and one distinct `mirror_text` among slim trials (same check as `transform.py`). Raise `ValueError` on conflict.

**Do not** build this dataset by filtering `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`. Derive from results-full so rater counts and unanimity come from one source.

### Output columns (exact order)

| Column | Type / meaning |
|--------|----------------|
| `message_id` | string alias of `post_id` |
| `original_text` | stable original post text |
| `mirror_text` | stable mirror text |
| `decision` | `keep` or `remove` (unanimous label) |
| `keep_remove_label` | `0` keep / `1` remove |
| `n_raters` | integer ≥ 3 |

No other columns in the committed CSV.

### Acceptance counts (current raw full results)

Measured against today’s `STUDY_PHASE_2_PART_2_RESULTS_FULL` after the frozen rule:

| Metric | Expected |
|--------|----------|
| Output rows | 1644 |
| `decision == keep` | 1490 |
| `decision == remove` | 154 |

If regeneration after a raw-data update changes these counts, update the README expected-size line in Step 3; do not silently change the inclusion rule.

### Public transform API (names frozen for Step 2)

| Symbol | Role |
|--------|------|
| `OUTPUT_CSV` | Path to `keep_remove_labels_unanimous_min3.csv` next to the transform module |
| `build_keep_remove_labels_unanimous_min3(raw=None) -> DataFrame` | Pure build; loads results-full when `raw` is omitted |
| `write_keep_remove_labels_unanimous_min3(path=OUTPUT_CSV) -> DataFrame` | Write CSV + return frame |

## Exact commands

Reconfirm measured counts (must match table above before coding):

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
trials = raw.copy()
trials["evaluation_mode"] = trials["evaluation_mode"].astype(str).str.lower().str.strip()
trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
trials = trials[trials["evaluation_mode"] == "linked_fate"]
trials = trials[trials["decision"].isin(["keep", "remove"])]
trials = trials[trials["post_id"].notna()].copy()
trials["post_id"] = trials["post_id"].astype(str).str.strip()
trials = trials[(trials["post_id"] != "") & (trials["post_id"].str.lower() != "nan")]
g = trials.groupby("post_id").agg(
    n_raters=("decision", "size"),
    n_unique=("decision", "nunique"),
    keep_count=("decision", lambda s: int((s == "keep").sum())),
)
filt = g[(g["n_raters"] >= 3) & (g["n_unique"] == 1)]
keep_n = int((filt["keep_count"] == filt["n_raters"]).sum())
print({"rows": len(filt), "keep": keep_n, "remove": len(filt) - keep_n})
PY
```

**Expected stdout:**

```text
{'rows': 1644, 'keep': 1490, 'remove': 154}
```

## Pass / fail

**Pass**

- Contracts above are accepted as written (or explicitly revised in this plan packet).
- Count command prints exactly `1644` / `1490` / `154` on current data.

**Fail**

- Counts differ → stop; investigate raw data drift or rule mismatch before Step 2.
- Desire to filter modal labels CSV instead of results-full → reject; revise plan first.

## Commit gate

No code commit required for this step. Proceed to Step 2 only after the count command matches.
