# Step 1: Build Part 2 and Part 3 union modal and unanimous label sets in the shared data layer

Notation: `P` = `/workspace/experiments/finetune_qwen_model_2026_08_08/`.

## Scope

- **Caller:** `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/transform.py` `__main__` and `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/transform_keep_remove_labels_unanimous_min3.py` `__main__`
- **Task:** Extract shared keep/remove aggregation from Part 2 into `/workspace/shared/data/transformed/keep_remove_aggregation.py`, refactor Part 2 builders to import it and stay byte-identical, add union builders that load `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`, register two transformed datasets, add pytest coverage, write union label CSVs to S3 (not git), and print counts.
- **Out of scope:** Experiment folder `experiments/finetune_lora_phase2_part3_2026_09_24/`, splits, chat JSONL, SageMaker, prior package P, editing raw union CSVs, `attention_check_passed` filtering.

## Dependencies

- Union raw table on S3 at `shared/data/raw/study_phase_2_part_2_and_3/results/full.csv` (registry `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`, 168,871 rows; added on main by PR #311; loaded via `/workspace/shared/data/dataloader.py`).
- Part 2 transformed CSVs on disk for a sha256 baseline before refactor.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md` | Decisions and pool table; Step 1 scope, byte-identical Part 2 rule |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | Modal logic to extract |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` | Unanimous logic to extract |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Documented filter and aggregation rules |
| `/workspace/shared/data/registry.py` | `DatasetEntry` pattern; `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` registered |
| `/workspace/shared/data/dataloader.py` | `load_dataset` for default `raw=None` loads from S3 |
| `/workspace/shared/data/raw/study_phase_2_part_2_and_3/README.md` | Union raw export metadata |
| `/workspace/.cursor/skills/implement-from-spec/SKILL.md` | Phased workflow |

## Files allowed to change

- `/workspace/shared/data/transformed/keep_remove_aggregation.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py`
- `/workspace/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py`
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/__init__.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/transform.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/transform_keep_remove_labels_unanimous_min3.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/tests/__init__.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/tests/conftest.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/tests/test_transform.py` (new)
- `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/tests/test_transform_unanimous_min3.py` (new)
- `/workspace/shared/data/registry.py`

Union label CSVs (`keep_remove_labels.csv`, `keep_remove_labels_unanimous_min3.csv`) are written to S3 at `shared/data/transformed/study_phase_2_part_2_and_3/` keys; do not commit them to git.

## Files forbidden to change

- `/workspace/shared/data/raw/**`
- `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv` (byte-identical to pre-refactor sha256)
- `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv` (byte-identical to pre-refactor sha256)
- `/workspace/shared/data/transformed/study_phase_2_part_2/main.py`
- `/workspace/shared/data/transformed/study_phase_2_part_2/transform_get_user_reflection_feedback.py`
- `/workspace/experiments/**`, `/workspace/tests/**`, `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-24_finetune_lora_phase2_part3_c5bcbf/plan.md`

## Public contracts

Extract current Part 2 behavior exactly when `dedupe_worker_post=False`. Union builders pass `dedupe_worker_post=True`. Do not filter on `trial_type` or `attention_check_passed`.

### `keep_remove_aggregation.py`

- `filter_keep_remove_trials(raw: pd.DataFrame, *, dedupe_worker_post: bool = False) -> pd.DataFrame`: lowercase/strip `decision` and `evaluation_mode`; keep `linked_fate` and `decision` in `{"keep","remove"}`; drop null, empty, or `"nan"` `post_id`; raise `KeyError` on missing `evaluation_mode`, `post_id`, or `decision`. When `dedupe_worker_post=True`: drop all rows for any `(prolific_id, post_id)` pair whose decisions conflict; then keep the earliest row per `(prolific_id, post_id)` by original CSV row order (preserve order with a row index before dedupe). When `dedupe_worker_post=False`, skip dedupe (Part 2 byte-identical path).
- `aggregate_modal_labels(trials: pd.DataFrame) -> pd.DataFrame`: require `post_id`, `original_text`, `mirror_text`, `decision`; raise `ValueError` on text conflicts per `post_id`; modal is `keep` only when `keep_count > remove_count` (ties `remove`); `keep_remove_label` is `1` for remove, `0` for keep; `n_raters` is unique `prolific_id` count per post; rename `post_id` to `message_id`; columns `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`, `n_raters`.
- `aggregate_unanimous_labels(trials: pd.DataFrame, *, min_raters: int = 3) -> pd.DataFrame`: same text check; per `post_id` count trial rows as `n_raters` (matches Part 2 byte-identical rule; equals unique `prolific_id` after union dedupe); keep when `n_raters >= min_raters` and all decisions agree; same `keep_remove_label` rule; columns add `n_raters` after modal columns.

### Part 2 wrappers (signatures unchanged)

`build_keep_remove_labels` / `write_keep_remove_labels` default-load `STUDY_PHASE_2_PART_2_RESULTS_FULL`, call `filter_keep_remove_trials(..., dedupe_worker_post=False)`, write `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv`. `build_keep_remove_labels_unanimous_min3` / `write_keep_remove_labels_unanimous_min3` use the same dedupe flag, write `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv`.

### Union builders (same public names; modal adds `n_raters`)

`study_phase_2_part_2_and_3/transform.py`: `build_keep_remove_labels` / `write_keep_remove_labels` default-load `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`, call `filter_keep_remove_trials(..., dedupe_worker_post=True)`, write `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels.csv` to S3. `study_phase_2_part_2_and_3/transform_keep_remove_labels_unanimous_min3.py`: unanimous pair uses the same dedupe flag, writes `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels_unanimous_min3.csv` to S3.

### Registry entries

- `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS` → `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels.csv`, `kind="transformed"`, `study_phase="study_phase_2_part_2_and_3"`.
- `STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` → `shared/data/transformed/study_phase_2_part_2_and_3/keep_remove_labels_unanimous_min3.csv`, same metadata.

## Pytest files

Under `/workspace/shared/data/transformed/study_phase_2_part_2_and_3/tests/`. Use small in-memory frames in `conftest.py`. Do not read `full.csv`.

### `tests/test_transform.py`

Classes `TestFilterKeepRemoveTrials`, `TestAggregateModalLabels`.

```text
given linked_fate, single, practice, empty post_id, and decision "KEEP" rows
when filter_keep_remove_trials with dedupe_worker_post False
then only linked_fate keep or remove rows with usable post_id remain

given worker W1 rates post X1 keep then remove (two rows, row order preserved)
when filter_keep_remove_trials with dedupe_worker_post True
then no rows remain for (W1, X1)

given worker W1 rates post X1 keep twice (non-conflicting duplicate)
when filter_keep_remove_trials with dedupe_worker_post True
then the earliest row by original order remains

given worker W1 rates post X1 keep twice (non-conflicting duplicate)
when filter_keep_remove_trials with dedupe_worker_post False
then both rows remain (Part 2 byte-identical path)

given post A (2 keep, 1 remove) and post B (1 keep, 1 remove)
when aggregate_modal_labels
then A is keep and B is remove

given post C with tied keep and remove counts
when aggregate_modal_labels
then C is remove

given post H with three unique raters (two keep, one remove)
when aggregate_modal_labels
then n_raters is 3 and decision is keep

given one post_id with conflicting original_text
when aggregate_modal_labels
then raise ValueError
```

### `tests/test_transform_unanimous_min3.py`

Class `TestAggregateUnanimousLabels`.

```text
given post D (3 keep) and post E (2 keep)
when aggregate_unanimous_labels with min_raters 3
then D has n_raters 3 and decision keep; E is absent

given post F with split decisions across 4 trials
when aggregate_unanimous_labels
then F is absent

given post G with 4 remove ratings
when aggregate_unanimous_labels
then decision is remove and keep_remove_label is 1
```

## Main caller

Part 2 sha256 before refactor:

```bash
sha256sum /workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv \
  /workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels_unanimous_min3.csv
```

Expected:

```text
2d88b242315d9ce985e5f9031433026937aafe4e26db11bc8b861f6319e0fef2  .../keep_remove_labels.csv
a789dd61c7764b39311e258217604ff9002b2744c7b6f35fb8b96b601b424fdf  .../keep_remove_labels_unanimous_min3.csv
```

Re-run Part 2 (sha256 must match):

```bash
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform.py
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
```

Expected: `rows=8791` `{'keep': 5978, 'remove': 2813}`; `rows=1644` `{'keep': 1490, 'remove': 154}`.

Build union labels (writes to S3):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2_and_3/transform.py
PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2_and_3/transform_keep_remove_labels_unanimous_min3.py
```

Expected: `rows=20000` `{'keep': 15196, 'remove': 4804}`; `rows=5715` `{'keep': 5280, 'remove': 435}`. Trial rows after dedupe: 100,606 (414 conflicting worker-post pairs, 2,454 rows dropped). Seven thousand six hundred fifty-three posts were rated in both parts; overlapping posts have identical text; no worker is in both parts.

```bash
PYTHONPATH=. uv run pytest shared/data/transformed/study_phase_2_part_2_and_3/tests -q
```

Expected: exit 0.

## Must pass

- Part 2 CSV sha256 unchanged; union counts match Main caller.
- Registry resolves both new names via `load_dataset`.
- Union modal CSV includes `n_raters`; Part 2 modal column order unchanged (no `n_raters`).
- Pytest exits 0.

## Must fail

- Part 2 sha256 change after re-run.
- Modal ties labeled `keep`; unanimous posts with `< 3` raters or split votes.
- `attention_check_passed` filtering; Part 2 builders calling dedupe with `True`; union builders calling dedupe with `False`.
- Missing union registry entries.
- Committing union label CSVs to git.

## Implement-from-spec notes

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md` in full auto mode. Phase 1: union `__main__` callers. Phase 2: scaffold stubs and registry constants. Phase 3: lock signatures. Phase 4: pytest from given/when/then blocks. Phase 5, one commit per unit: (1) `filter_keep_remove_trials`, (2) `aggregate_modal_labels`, (3) `aggregate_unanimous_labels`, (4) Part 2 refactor plus sha256 check, (5) union builders and live commands. Phase 6: pytest green, Part 2 sha256 match, union counts match.
