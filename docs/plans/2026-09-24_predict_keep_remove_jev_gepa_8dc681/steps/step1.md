# Step 1: Scaffold experiment folder, dependencies, and tracking

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/wandb_tracking.py` `init_run`
- **Task:** Create the experiment folder with README, SETUP, and RESULTS stubs. Scaffold `shared/` and `shared/tests/` with empty `__init__.py` files. Add `typesafe-sdk==0.7.1` and `gepa==0.1.4` to `pyproject.toml` and refresh `uv.lock`. Confirm `wandb` is already available via the `dev` dependency group (installed by default `uv sync`). Copy S3 helpers into `artifacts.py`. Build `wandb_tracking.py` with project, entity, group, `job_type`, and run-name conventions from design.md. Build `secrets.py` for API key resolution (env first, then AWS Secrets Manager).
- **Out of scope:** `cohort.py`, `splits.py`, `prompt.py`, `jev_scorer.py`, rate limiter, retries, latency, pricing, metrics, `jev_baseline/`, `jev_gepa/`, `analysis/`, live Jev calls, GEPA optimization, editing `shared/data/registry.py`, editing `webapp/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md` | Experiment name, S3 prefix, Wandb project URL |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Folder layout, Wandb conventions, S3 subprefixes, verification pytest command |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/artifacts.py` | `download_if_missing`, `upload_under_prefix` pattern with `CampaignObjectStore` |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` | `OUTPUT_S3_BUCKET`, `EXPERIMENT_S3_PREFIX` naming pattern |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner text |
| `/workspace/lib/load_env_vars.py` | `EnvVarsContainer.get_env_var` for `WANDB_API_KEY` and `OPENAI_API_KEY` |
| `/workspace/pyproject.toml` | Current dependencies; `wandb` lives in `[dependency-groups] dev` |
| `/tmp/jev_probe/run_probe.py` | `load_api_key()` pattern for Secrets Manager secret `jev-typesafe-api-key` (JSON or raw string) |
| `/workspace/AGENTS.md` | README is 1 to 2 lines plus redirect; SETUP names data requirements only |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/README.md` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/SETUP.md` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/artifacts.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/wandb_tracking.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/secrets.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/conftest.py` (new, empty or minimal)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_artifacts.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_wandb_tracking.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_secrets.py` (new)
- `/workspace/pyproject.toml` (add `typesafe-sdk==0.7.1`, `gepa==0.1.4`)
- `/workspace/uv.lock` (regenerated)
- `/workspace/.gitignore` (ignore `experiments/predict_keep_remove_jev_gepa_2026_09_23/outputs/` and `**/__pycache__/` under this experiment only, if not already covered)

## Files forbidden to change

- `/workspace/webapp/**`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/data/raw/study_phase_2_part_3/**`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## README and SETUP contract

Write `README.md` first.

`README.md` must:

1. Start with the same agent read-only banner from `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Use one or two lines naming the experiment, then redirect to `SETUP.md` and `RESULTS.md`.

`SETUP.md` must name data requirements only (no environment setup):

1. Registry dataset `STUDY_PHASE_2_PART_3_RESULTS_FULL` at `shared/data/raw/study_phase_2_part_3/results/full.csv` (131,175 rows, frozen 2026-09-22 snapshot).
2. Registry dataset `STUDY_PHASE_2_PART_3_STIMULI` at `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv` (18,899 posts).
3. S3 artifact prefix `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/`.
4. Wandb project `predict_keep_remove_jev_gepa_2026_09_23` under entity `mind_technology_lab`.

`RESULTS.md` must be a stub with the title and a single line: `Stage A and Stage B tables will be written here.`

## Contracts

Pinned constants (module-level in `artifacts.py` and `wandb_tracking.py`; no separate `constants.py` in design.md):

- `OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"`
- `EXPERIMENT_DIRNAME = "predict_keep_remove_jev_gepa_2026_09_23"`
- `EXPERIMENT_S3_PREFIX = "experiments/predict_keep_remove_jev_gepa_2026_09_23"`
- `WANDB_PROJECT = "predict_keep_remove_jev_gepa_2026_09_23"`
- `WANDB_ENTITY = "mind_technology_lab"`
- `AWS_SECRETS_REGION = "us-east-2"`

### `artifacts.py`

Reuse `CampaignObjectStore` from `data_platform.generate_features.s3_feature_campaign`. Reuse `REPO_ROOT` from `lib.constants`.

```python
def download_if_missing(path: Path, key: str) -> None:
    """Write ``key`` from S3 when the local file is absent. Raise FileNotFoundError when missing on S3."""

def upload_under_prefix(path: Path, allowed_prefix: str = EXPERIMENT_S3_PREFIX) -> None:
    """Upload ``path`` with put_new when absent, else replace. Refuse keys outside ``allowed_prefix``."""
```

`upload_under_prefix` derives the S3 key from `path.relative_to(REPO_ROOT)` (same pattern as reasoning-during-moderation).

### `secrets.py`

```python
def get_secret_value(secret_id: str, *, env_var: str | None = None) -> str:
    """Return env var when set and non-empty; else fetch Secrets Manager ``secret_id`` in us-east-2.
    Parse JSON secrets by checking keys api_key, TYPESAFE_API_KEY, key, then first value."""

def get_jev_api_key() -> str:
    """Return Jev TypeSafe API key from TYPESAFE_API_KEY env or secret jev-typesafe-api-key."""

def get_wandb_api_key() -> str:
    """Return Wandb API key from WANDB_API_KEY env (via EnvVarsContainer) or secret wandb-api-key."""

def get_openai_api_key() -> str:
    """Return OpenAI API key from OPENAI_API_KEY env (via EnvVarsContainer) or secret openai-api-key."""
```

Raise `ValueError` with the secret id when both env and Secrets Manager are empty.

### `wandb_tracking.py`

```python
@dataclass(frozen=True)
class WandbRunSpec:
    group: str          # jev_baseline | jev_gepa | analysis
    name: str           # e.g. A1_pair_study_prompt
    job_type: str       # score | optimize | evaluate | analyze
    config: dict[str, object]

def init_run(spec: WandbRunSpec) -> Any:
    """Call wandb.login(key=get_wandb_api_key()) then wandb.init with project, entity, group, name, job_type, config."""
```

`init_run` must set `wandb.Run.config` keys when callers pass `model`, `batch_size`, `rate_cap`, `split_hash`, `prompt_hash` in `spec.config`.

```python
def log_artifact(run: Any, path: Path, name: str, artifact_type: str) -> None:
    """Log a local file as a Wandb artifact on the active run."""
```

Do not call `wandb.init` at import time.

## Tests to write first

Tests live under `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/`. No live AWS, S3, or Wandb calls. Patch with `unittest.mock`.

### `tests/test_artifacts.py`

Class `TestUploadUnderPrefix`.

```text
given a local file under experiments/predict_keep_remove_jev_gepa_2026_09_23/data/foo.parquet
when upload_under_prefix with allowed_prefix experiments/predict_keep_remove_jev_gepa_2026_09_23
then CampaignObjectStore.put_new is called once with key experiments/predict_keep_remove_jev_gepa_2026_09_23/data/foo.parquet

given the same file and store.get returns an existing object
when upload_under_prefix
then store.replace is called with the existing etag

given a path whose relative key starts with experiments/other/
when upload_under_prefix
then raise ValueError
```

Class `TestDownloadIfMissing`.

```text
given a local file already on disk
when download_if_missing
then CampaignObjectStore.get is not called

given a missing local file and store.get returns bytes
when download_if_missing
then the file is written and parent directories exist

given a missing local file and store.get returns None
when download_if_missing
then raise FileNotFoundError
```

### `tests/test_secrets.py`

Class `TestGetSecretValue`.

```text
given os.environ TYPESAFE_API_KEY=abc
when get_jev_api_key
then return abc and boto3 is not called

given empty env and Secrets Manager returns raw string sk-test
when get_jev_api_key
then return sk-test

given empty env and Secrets Manager returns JSON {"api_key": "from-json"}
when get_jev_api_key
then return from-json

given empty env and Secrets Manager returns empty string
when get_jev_api_key
then raise ValueError mentioning jev-typesafe-api-key
```

### `tests/test_wandb_tracking.py`

Class `TestInitRun`.

```text
given WandbRunSpec group=jev_baseline name=A1_pair_study_prompt job_type=score config={}
when init_run with wandb.login and wandb.init patched
then wandb.init is called with project predict_keep_remove_jev_gepa_2026_09_23 entity mind_technology_lab group jev_baseline name A1_pair_study_prompt
and job_type score is in the init kwargs config or tags per wandb API used
```

## Implementation order

Follow `/implement-from-spec`. Full auto. One commit per unit of work.

1. `README.md`, `SETUP.md`, `RESULTS.md`, `shared/__init__.py`, `shared/tests/__init__.py`, `.gitignore` entries
2. `pyproject.toml` dependency pins and `uv lock`
3. `artifacts.py` contract stubs
4. `secrets.py` contract stubs
5. `wandb_tracking.py` contract stubs
6. pytest files from the given/when/then blocks (failing)
7. `secrets.py` implementation until `test_secrets.py` is green
8. `artifacts.py` implementation until `test_artifacts.py` is green
9. `wandb_tracking.py` implementation until `test_wandb_tracking.py` is green

## Commands

Install and lock:

```bash
cd /workspace
uv lock
uv sync --frozen
```

Expected: exit 0. `uv run python -c "import typesafe_sdk, gepa, wandb; print(typesafe_sdk.__version__)"` prints `0.7.1` (or the pinned version) and imports succeed.

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q
```

Expected: exit 0.

Optional live Wandb auth check (after AWS keys exported):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run
spec = WandbRunSpec(group='jev_baseline', name='step1_smoke', job_type='score', config={'step': 1})
run = init_run(spec)
print('wandb_run_id=', run.id)
run.finish()
"
```

Expected: prints a non-empty `wandb_run_id=` without authentication error.

## Must pass

- `experiments/predict_keep_remove_jev_gepa_2026_09_23/README.md` redirects to `SETUP.md` and `RESULTS.md`.
- `SETUP.md` names both registry datasets and the S3 prefix.
- `typesafe-sdk==0.7.1` and `gepa==0.1.4` appear in `pyproject.toml` and `uv.lock`.
- `wandb` imports after `uv sync` (from dev group).
- `PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q` exits 0.
- `upload_under_prefix` refuses keys outside `experiments/predict_keep_remove_jev_gepa_2026_09_23`.
- `get_jev_api_key` reads env before Secrets Manager.

## Must fail

- Uploading to `s3://jspsych-mirror-view-2026-09-09/`.
- Calling `wandb.init` without resolving an API key.
- Adding `cohort.py`, `prompt.py`, or `jev_scorer.py` in this step.
- Editing `shared/data/registry.py`.
- Writing metric tables into `RESULTS.md` (stub only).

## Commit messages

1. `scaffold predict_keep_remove_jev_gepa experiment docs and shared package`
2. `add typesafe-sdk and gepa dependencies`
3. `add experiment artifacts and secrets helpers`
4. `add wandb tracking helpers for predict_keep_remove_jev_gepa`
5. `add shared tests for artifacts secrets and wandb tracking`

## Implement-from-spec notes

Phase 1 names `wandb_tracking.init_run` as the caller. Phase 2 scaffolds modules with stub bodies. Phase 3 locks signatures above; bodies stay `raise NotImplementedError` until Phase 5. Phase 4 writes pytest files that fail for `NotImplementedError`, not import errors. Phase 5 follows the implementation order list. Phase 6 completes when pytest exits 0.
