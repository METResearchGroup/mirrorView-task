# Step 1: Lock shared package layout, registry names, and matching-output contract

## Goal

Create `/workspace/shared/textual_features/` so it matches the finalized tree in the parent plan. Fix the `CalculateMetric` contract and the registry catalog surface. Add failing unit tests that pin metric names and known-input outputs against today's experiment implementations. Do not put real metric math or language-model calls in this step. Use stubs only.

## Caller / unit of work

**Main caller (this step):** pytest under `/workspace/shared/textual_features/tests/`.

1. Import `CalculateMetric` from `shared.textual_features.base`.
2. Import registry constants and `get_feature` from `shared.textual_features.registry`.
3. Assert every length and readability registry name resolves to a stub entry whose `build().name` matches the fixed metric `name` field.
4. Assert that `calculate` paths fail (or raise `NotImplementedError`) so Step 2 can make them pass against the matching-output fixtures.

**Slice:** package tree, contracts, and failing tests.

**Out of scope:** implementing `calculate` or classifier bodies; migrating experiment files; spaCy install changes; live OpenAI calls.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-08-09_shared_textual_features_642074/plan.md` | Finalized tree, registry names, example API |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/interfaces.py` | Source `CalculateMetric` base class to move |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/metrics.py` | Current length metric classes and names |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/metrics.py` | Current readability metric classes and names |
| `/workspace/shared/data/registry.py` | Catalog, `get_*`, and KeyError pattern to copy |

## Files allowed to change

- `/workspace/shared/textual_features/__init__.py` (create)
- `/workspace/shared/textual_features/base.py` (create)
- `/workspace/shared/textual_features/text_utils.py` (create; stub exports only)
- `/workspace/shared/textual_features/registry.py` (create; catalog and stubs)
- `/workspace/shared/textual_features/char_count.py` (create; stub class)
- `/workspace/shared/textual_features/word_count.py` (create; stub class)
- `/workspace/shared/textual_features/sentence_count.py` (create; stub class)
- `/workspace/shared/textual_features/avg_sentence_length.py` (create; stub class)
- `/workspace/shared/textual_features/punctuation_count.py` (create; stub class)
- `/workspace/shared/textual_features/punctuation_density.py` (create; stub class)
- `/workspace/shared/textual_features/flesch_kincaid_grade.py` (create; stub class)
- `/workspace/shared/textual_features/reading_ease.py` (create; stub class)
- `/workspace/shared/textual_features/valence.py` (create; stub classify_* raising NotImplementedError)
- `/workspace/shared/textual_features/intergroup.py` (create; stub classify_* raising NotImplementedError)
- `/workspace/shared/textual_features/prime.py` (create; stub classify_* raising NotImplementedError)
- `/workspace/shared/textual_features/tests/__init__.py` (create; empty is fine)
- `/workspace/shared/textual_features/tests/test_length_metrics.py` (create; failing matching-output tests)
- `/workspace/shared/textual_features/tests/test_readability_metrics.py` (create; failing matching-output tests)
- `/workspace/shared/textual_features/tests/test_registry.py` (create; catalog completeness tests)

## Files forbidden to change

- `/workspace/experiments/mirrors_content_analysis_2026_04_24/**` (migration is Step 4)
- `/workspace/experiments/predict_keep_remove_2026_05_07/**`
- `/workspace/shared/data/**`
- `/workspace/pyproject.toml` (no new dependencies in this step)

## Contracts to freeze

### `CalculateMetric` (`shared/textual_features/base.py`)

Same abstract surface as today's experiment interface:

```text
property name(self) -> str
describe(self) -> str
calculate(self, text: str) -> float
```

### `FeatureEntry` (`shared/textual_features/registry.py`)

```text
FeatureEntry(
  name: str,                          # SCREAMING_SNAKE registry key
  kind: "metric" | "classifier",
  metric_name: str | None,            # e.g. "char_count"; None for classifiers
  build: Callable[[], CalculateMetric] | None,   # metrics only
  classify_post: Callable[[str], Any] | None,    # classifiers only
)
```

### Registry API

```text
FEATURES: dict[str, FeatureEntry]
get_feature(name: str) -> FeatureEntry
# KeyError message must list valid names (same style as shared.data.registry.get_dataset)
```

### Registry constants (must exist as module-level strings)

`CHAR_COUNT`, `WORD_COUNT`, `SENTENCE_COUNT`, `AVG_SENTENCE_LENGTH`, `PUNCTUATION_COUNT`, `PUNCTUATION_DENSITY`, `FLESCH_KINCAID_GRADE`, `READING_EASE`, `VALENCE`, `INTERGROUP`, `PRIME`.

### Stub behavior

- Metric `calculate` bodies: `raise NotImplementedError` (or equivalent) until Step 2.
- Classifier `classify_post` / `classify_texts`: `raise NotImplementedError` until Step 3.
- `name` / `describe` on metric stubs may return the final strings now (allowed, because that helps registry tests).

### Matching-output fixtures (encode in tests now; implement in Step 2)

Use these exact inputs so Step 2 has a fixed target:

| Input text | Metric | Expected |
|------------|--------|----------|
| `"Hello world!"` | `char_count` | `12.0` |
| `"Hello world!"` | `word_count` | `2.0` |
| `"Hello world!"` | `sentence_count` | `1.0` |
| `"Hello world!"` | `avg_sentence_length` | `2.0` |
| `"Hello world!"` | `punctuation_count` | `1.0` |
| `"Hello world!"` | `punctuation_density` | `1.0 / 12.0` |
| `""` | all length metrics above | `0.0` |
| `"Hello world."` | `flesch_kincaid_grade` | value from **current** `FleschKincaidGradeMetric().calculate("Hello world.")` captured once into the test as a literal |
| `"Hello world."` | `flesch_reading_ease` | value from **current** `FleschReadingEaseMetric().calculate("Hello world.")` captured once into the test as a literal |

Before writing the readability expected literals, run the capture command in Exact commands and paste the floats into the tests.

## Exact commands

```bash
cd /workspace

# Capture readability matching-output literals from current experiment classes (run before finalizing tests)
PYTHONPATH=. uv run python - <<'PY'
from experiments.mirrors_content_analysis_2026_04_24.analysis.readability_complexity_analysis.metrics import (
    FleschKincaidGradeMetric,
    FleschReadingEaseMetric,
)
text = "Hello world."
print("FK", FleschKincaidGradeMetric().calculate(text))
print("RE", FleschReadingEaseMetric().calculate(text))
PY

# After scaffold + failing tests:
PYTHONPATH=. uv run pytest shared/textual_features/tests/ -q
```

**Expected after this step:** pytest exits non-zero. Failures are assertion errors or `NotImplementedError` from unimplemented `calculate`. Registry completeness asserts that wait on Step 2 wiring are fine only if the test file documents that. Every tree file listed above exists.

## Pass / fail for this step

**Pass when:**
1. Every path in the finalized tree under `shared/textual_features/` exists (including `tests/`).
2. `CalculateMetric`, `FeatureEntry`, registry constants, and `get_feature` are importable.
3. `test_registry.py` asserts all 11 registry names are present in `FEATURES`.
4. Length and readability tests exist with the matching-output fixtures above, and they fail for the right reason (stubs, not import errors).
5. No experiment files were modified.

**Fail when:** metric formulas are copied into shared (that is Step 2); experiment modules are migrated (Step 4); tests pass because stubs accidentally return plausible values; spaCy or OpenAI work is started here.
