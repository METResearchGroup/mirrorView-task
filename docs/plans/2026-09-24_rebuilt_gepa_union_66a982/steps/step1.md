# Step 1: Scaffold rebuilt package and tracking

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` `main` (stub) and `shared/wandb_tracking.py` `init_run`
- **Task:** Create the `jev_gepa_rebuilt/` package with a short README, package `__init__.py`, pinned constants, stub `optimize.py` and `evaluate.py` CLIs, and S3 upload helpers that reuse `shared/artifacts.py` under the `jev_gepa_rebuilt/` S3 subprefix. Register Wandb group `jev_gepa_rebuilt`. Add unit tests for constants and upload key prefix. Do not copy Stage B `jev_gepa/` code in this step, except for import patterns the stubs need.
- **Out of scope:** Prompt flip, adapter scoring, GEPA policies, dev-A/dev-B split, guards, live Jev or GEPA runs, editing `jev_gepa/` or `webapp/`.

## Dependencies

Union parquet must exist at `experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_union_splits.parquet` (from the `shared/splits.py` union build). Step 1 tests may use a temporary parquet path. Production code must import `COHORT_UNION_PARQUET` from `shared/splits.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md` | S3 prefix, Wandb group, ablation ids |
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` | Folder layout, artifact filenames |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | Path bootstrap, `OUTPUT_ROOT`, CLI shape |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/artifacts.py` | `upload_under_prefix`, bucket constants |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/wandb_tracking.py` | `WandbRunSpec`, `init_run` |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py` | `COHORT_UNION_PARQUET` |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/README.md` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/constants.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/artifacts.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` (new, stub CLI)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py` (new, stub CLI)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/conftest.py` (new, minimal)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_constants.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_artifacts.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_optimize_cli.py` (new)
- `/workspace/.gitignore` (ignore `jev_gepa_rebuilt/outputs/` if not already covered)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/**`
- `/workspace/webapp/**`
- `/workspace/pyproject.toml`
- `/workspace/shared/data/registry.py`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md`

## Contracts

### `README.md`

Write one or two lines. State that this is rebuilt GEPA on the union cohort, and point to experiment `SETUP.md`, `RESULTS.md`, and this plan folder.

### `constants.py`

```python
WANDB_GROUP = "jev_gepa_rebuilt"
REBUILT_S3_SUBPREFIX = "jev_gepa_rebuilt"  # under EXPERIMENT_S3_PREFIX
DEFAULT_MAX_METRIC_CALLS = 30_000
HALF_BUDGET_MAX_METRIC_CALLS = 15_000
GEPA_SEED = 20260924
REFLECTION_MINIBATCH_SIZE = 25
VAL_SUBSAMPLE_SIZE = 100
ACCEPTANCE_MARGIN_CORRECT = 2
STUDY_COMPONENT_KEY = "study_instruction"
OUTPUT_ROOT = Path("experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs")
GEPA_RUN_DIRNAME = "gepa_run"
GEPA_RESULT_FILENAME = "gepa_result.json"
DEV_SELECTION_FILENAME = "dev_selection.json"
CANDIDATE_DEV_SCORES_FILENAME = "candidate_dev_scores.jsonl"
```

Import cohort path:

```python
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET
```

### `artifacts.py`

```python
def rebuilt_s3_prefix() -> str:
    """Return experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt"""

def upload_rebuilt(path: Path) -> None:
    """Call shared artifacts.upload_under_prefix with allowed_prefix = rebuilt_s3_prefix()."""
```

### `optimize.py` (stub)

- Same repo-root `sys.path` bootstrap as `jev_gepa/optimize.py`.
- `argparse` with `--ablation-id`, `--smoke`, `--max-metric-calls`.
- `ABLATION_IDS` tuple listing `R1_gepa_pair`, `R2_majority_weighted`, `R3_gepa_pair_terra`, `R4_gepa_multi_component`, `R5_gepa_original`, `R6_gepa_mirror`, `R7_plain_majority`. R7 is approved and enabled.
- `main` prints `jev_gepa_rebuilt optimize stub` and exits 0 until Step 3 wires GEPA.

### `evaluate.py` (stub)

- `--ablation-id`, `--split` choices `dev` `test`.
- Prints `jev_gepa_rebuilt evaluate stub` and exits 0.

## Tests to write first

### `tests/test_constants.py`

Class `TestRebuiltConstants`.

```text
when importing constants
then WANDB_GROUP == "jev_gepa_rebuilt"
and DEFAULT_MAX_METRIC_CALLS == 30000
and STUDY_COMPONENT_KEY == "study_instruction"
and str(COHORT_UNION_PARQUET).endswith("cohort_union_splits.parquet")
```

### `tests/test_artifacts.py`

Class `TestUploadRebuilt`.

```text
given a file under jev_gepa_rebuilt/outputs/R1_gepa_pair/foo.json
when upload_rebuilt with CampaignObjectStore patched
then put_new key starts with experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/
```

### `tests/test_optimize_cli.py`

Class `TestOptimizeCli`.

```text
when running optimize.main with --ablation-id R1_gepa_pair --help via subprocess or argparse
then stdout mentions --max-metric-calls and R1_gepa_pair
```

## Implementation order

Follow `/implement-from-spec`. Full auto. One commit per unit of work.

1. Package dirs, `README.md`, `constants.py`, stub CLIs
2. pytest files (failing)
3. `artifacts.py` until `test_artifacts.py` is green
4. Wire constants test and CLI test until green

## Commands

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/ -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --help
```

Expected: stdout contains `--max-metric-calls` and `R1_gepa_pair`.

```bash
PYTHONPATH=. uv run python -c "
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import WANDB_GROUP
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run
from unittest.mock import patch
spec = WandbRunSpec(group=WANDB_GROUP, name='step1_smoke', job_type='optimize', config={})
with patch('wandb.init'), patch('wandb.login'):
    init_run(spec)
print('wandb_group_ok')
"
```

Expected stdout: `wandb_group_ok`

## Must pass

- `jev_gepa_rebuilt/` exists with tests green.
- S3 uploads use prefix `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/`.
- Wandb group constant is `jev_gepa_rebuilt`.
- Stub optimize CLI accepts union ablation ids.

## Must fail

- Uploading under `jev_gepa/outputs/` via rebuilt helper.
- Importing Stage B adapter from `jev_gepa_rebuilt` in this step.
- Changing `jev_gepa/` modules.

## Commit message

`scaffold jev_gepa_rebuilt package constants artifacts and stub CLIs`

## Done check

- `PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/ -q` exits 0.
- Optimize `--help` works for `R1_gepa_pair`.
