# Step 2: Prompt and adapter flip for study-instruction optimization

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/adapter.py` `JevGepaRebuiltAdapter.evaluate`
- **Task:** Split prompt rendering so GEPA mutates `study_instruction` while Jev state carries post bodies only and the per-post task question stays fixed. Port adapter logic from `jev_gepa/adapter.py` with `remove_share` on instances, score modes **R1** (`label_certainty`), **R2** (`majority_weighted`), **R7** (`plain_majority`), richer reflection feedback fields, and **post-count** `num_metric_calls` (sum of posts scored, not HTTP batches). Add a study-flip scoring entrypoint in `shared/jev_scorer.py` that the rebuilt adapter calls.
- **Out of scope:** GEPA `gepa.optimize` wiring, custom val/acceptance/sampler policies (Step 3), dev-A/dev-B selection, guards, editing `jev_gepa/optimize.py`.

## Dependencies

Step 1 must provide `jev_gepa_rebuilt/constants.py` (`STUDY_COMPONENT_KEY`, score mode names).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` | Prompt architecture, score formulas, budget unit |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/adapter.py` | Current adapter, trajectories, reflection dataset |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py` | `STUDY_INSTRUCTION`, `render_state_text`, `build_noul_instruction` |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` | `score_batch`, `_build_questions_with_instruction` |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py` | `COHORT_UNION_PARQUET`, `remove_share` column |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_render_posts_only.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_jev_scorer_study_flip.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/adapter.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/scoring.py` (new, thin wrapper if needed)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_adapter_scores.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_adapter_metric_calls.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_reflective_dataset.py` (new)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/adapter.py`
- `/workspace/webapp/**`
- `/workspace/pyproject.toml`

## Contracts

### Prompt flip (`shared/prompt.py`)

Add post-only state renderers (no study paragraphs in state):

```python
def render_posts_only_state(
    view: str,
    original_text: str,
    mirror_text: str,
    post_1_role: str,
) -> str:
    """Return Jev state text with Post 1 / Post 2 blocks and CLOSING_LINE only."""
```

Pair view matches current post blocks from `render_pair_prompt` but **without** `STUDY_INSTRUCTION` or addendum. Single views use one `Post 1:` block only.

Fixed per-post task text (not GEPA-mutated), taken from the current `build_noul_instruction` body **after** the ``Consider `posts[i]`. `` prefix:

```python
PAIR_TASK_INSTRUCTION = (
    "You are evaluating a pair of political social media posts shown together, "
    "including the study instructions and both post texts. "
    "Should this pair of posts be removed from the platform? "
    "Answer yes if both posts should be removed; answer no if both should be allowed."
)
SINGLE_TASK_INSTRUCTION = (
    "You are evaluating one political social media post. "
    "Should this post be removed from the platform? "
    "Answer yes if it should be removed; answer no if it should be allowed."
)

def task_instruction_for_view(view: str) -> str:
    """Return PAIR_TASK_INSTRUCTION or SINGLE_TASK_INSTRUCTION."""
```

Refactor `build_noul_instruction` to compose ``Consider `{slot}`. `` + `task_instruction_for_view(view)` so pair and single arms stay consistent.

Seed text for GEPA (not passed as Jev state):

```python
def default_study_instruction_seed(view: str) -> str:
    """Return STUDY_INSTRUCTION for pair; STUDY_INSTRUCTION_SINGLE for original|mirror."""
```

### Jev study-flip scoring (`shared/jev_scorer.py`)

Add:

```python
def score_batch_with_study_instruction(
    client: TypeSafeClient,
    state_texts: list[str],
    view: str,
    *,
    study_instruction: str,
    task_instruction: str | None = None,
) -> BatchResult:
    """Score post-only state texts.

    Noul instructions: Consider `posts[i]`. {task_instruction or task_instruction_for_view(view)}.
    Pass study_instruction into the TypeSafe call as the shared instruction field used by GEPA rebuild
    (same wire shape as legacy score_batch when instruction carried the mutating text; verify against
    fake-client tests).
    """
```

Do not break existing `score_batch` callers (Stage A/B). Rebuilt adapter must call only `score_batch_with_study_instruction`.

### `jev_gepa_rebuilt/adapter.py`

```python
ScoreMode = Literal["label_certainty", "majority_weighted", "plain_majority"]

@dataclass(frozen=True)
class JevDataInst:
    ...  # same as jev_gepa.adapter plus remove_share: float

class JevGepaRebuiltAdapter:
    def evaluate(...) -> EvaluationBatch:
        study_instruction = candidate[STUDY_COMPONENT_KEY]
        ...
```

**Per-example score** (`_score_example`):

| Mode | Formula |
|------|---------|
| `label_certainty` (R1) | `1.0 - abs(p_remove - remove_share)` |
| `majority_weighted` (R2) | `majority_prob * (0.5 if abs(n_keep - n_remove) == 1 else 1.0)` where `majority_prob = p_remove` if label remove else `1 - p_remove` |
| `plain_majority` (R7) | `majority_prob` with weight `1.0` |

**Metric calls:** in `_score_instances`, set `num_metric_calls += len(chunk)` (posts), not `+= 1`.

**GEPA candidate:** `seed_candidate = {STUDY_COMPONENT_KEY: default_study_instruction_seed(view)}`. Do not use legacy key `"instruction"`.

**Reflection:** extend `_build_feedback` to include `remove_share`, vote margin `abs(n_keep - n_remove)`, confident-error flag (`p_remove` far from 0.5 on wrong side). `make_reflective_dataset` returns `{STUDY_COMPONENT_KEY: records}`.

## Tests to write first

### `shared/tests/test_render_posts_only.py`

Class `TestRenderPostsOnlyState`.

```text
given pair view original/mirror roles
when render_posts_only_state
then output contains Post 1 and Post 2 blocks and CLOSING_LINE
and does not contain STUDY_INSTRUCTION opening sentence "pairs of real political"

given original view
when render_posts_only_state
then no Post 2 and no "political mirrors"
```

### `shared/tests/test_jev_scorer_study_flip.py`

Class `TestScoreBatchWithStudyInstruction`.

```text
given fake client capturing state and questions for one post
when score_batch_with_study_instruction with study_instruction="STUDY" and pair view
then state posts[0] is post-only text without "STUDY"
and Noul instructions contain PAIR_TASK_INSTRUCTION
and shared study text is passed per contract (assert on fake client kwargs)
```

### `jev_gepa_rebuilt/tests/test_adapter_scores.py`

Class `TestAdapterScoreModes`.

```text
given instance label=1 remove_share=0.8 p_remove=0.75
when label_certainty score
then score == 0.95

given instance label=0 n_keep=3 n_remove=2 p_remove=0.4
when majority_weighted score
then score == 0.6 * 0.5 == 0.3

given same instance with plain_majority
then score == 0.6

given instance n_keep=4 n_remove=1 (one-vote margin)
when majority_weighted
then weight is 0.5
```

Use a fake scorer returning fixed probabilities; no network.

### `jev_gepa_rebuilt/tests/test_adapter_metric_calls.py`

Class `TestAdapterMetricCalls`.

```text
given 25 instances and batch_size 10
when evaluate
then num_metric_calls on EvaluationBatch is 25 not 3
```

### `jev_gepa_rebuilt/tests/test_reflective_dataset.py`

Class `TestReflectiveDataset`.

```text
given one wrong trajectory with remove_share and n_keep/n_remove
when make_reflective_dataset
then Feedback contains remove_share and vote counts
and dataset key is study_instruction not instruction
```

## Implementation order

1. `render_posts_only_state`, task instruction constants, refactor `build_noul_instruction`
2. `score_batch_with_study_instruction` + shared tests
3. `adapter.py` scaffold + failing rebuilt tests
4. Score modes and metric call counting
5. Reflection feedback fields

## Commands

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_render_posts_only.py experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_jev_scorer_study_flip.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_adapter_scores.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_adapter_metric_calls.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_reflective_dataset.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python -c "
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import render_pair_prompt, render_posts_only_state
pair_full = render_pair_prompt('o','m','original', False)
posts_only = render_posts_only_state('pair','o','m','original')
assert 'pairs of real political' in pair_full
assert 'pairs of real political' not in posts_only
print('prompt_flip_ok')
"
```

Expected stdout: `prompt_flip_ok`

## Must pass

- Study text is not in Jev state on the rebuilt scoring path.
- `remove_share` required on `JevDataInst` loaded from union parquet.
- R1/R2/R7 score formulas match plan **Decisions made**.
- `EvaluationBatch.num_metric_calls` equals posts scored.

## Must fail

- Optimizing `build_noul_instruction` text via GEPA candidate key `instruction` only.
- Counting one metric call per HTTP batch in rebuilt adapter.
- Breaking `jev_gepa/adapter.py` behavior or its existing tests.

## Commit message

`flip prompts and jev_gepa_rebuilt adapter for study instruction scoring modes`

## Done check

- All commands above exit 0.
- `study_instruction` is the sole GEPA component key for R1/R2/R7 pair runs.
