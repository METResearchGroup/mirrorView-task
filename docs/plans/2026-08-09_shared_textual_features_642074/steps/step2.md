# Step 2: Implement deterministic length and readability modules plus registry

## Goal

Flesh every deterministic feature module and `text_utils.py` so `calculate` matches today’s experiment metrics byte-for-byte on the Step-1 fixtures. Wire `get_feature(...).build()` for all eight length/readability registry names. Turn length, readability, and registry tests green. Classifiers stay stubs.

## Caller / unit of work

**Main caller (this step):** pytest → `get_feature(CHAR_COUNT).build().calculate(text)` (and siblings).

1. Implement helpers in `text_utils.py` lifted from `analysis_utils.py` / readability private helpers.
2. Implement each length/readability metric class to parity with the experiment `metrics.py` sources.
3. Registry `build` callables return those classes.
4. Tests from Step 1 pass.

**Out of scope:** valence/intergroup/prime bodies; experiment migration; changing metric formulas; deleting experiment `metrics.py` yet.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/analysis_utils.py` | `WORD_RE`, `PUNCTUATION_RE`, `SENTENCE_SPLIT_RE`, `safe_divide` |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/metrics.py` | Source of truth for length formulas |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/metrics.py` | Source of truth for FK / reading ease + spaCy syllable path |
| `/workspace/docs/plans/2026-08-09_shared_textual_features_642074/steps/step1.md` | Frozen fixtures and contracts |
| `/workspace/shared/textual_features/tests/test_length_metrics.py` | Targets to make green |
| `/workspace/shared/textual_features/tests/test_readability_metrics.py` | Targets to make green |
| `/workspace/shared/textual_features/tests/test_registry.py` | Deterministic registry build checks |

## Files allowed to change

- `/workspace/shared/textual_features/text_utils.py`
- `/workspace/shared/textual_features/char_count.py`
- `/workspace/shared/textual_features/word_count.py`
- `/workspace/shared/textual_features/sentence_count.py`
- `/workspace/shared/textual_features/avg_sentence_length.py`
- `/workspace/shared/textual_features/punctuation_count.py`
- `/workspace/shared/textual_features/punctuation_density.py`
- `/workspace/shared/textual_features/flesch_kincaid_grade.py`
- `/workspace/shared/textual_features/reading_ease.py`
- `/workspace/shared/textual_features/registry.py` (wire metric `build` callables; do not implement classifiers)
- `/workspace/shared/textual_features/__init__.py` (export public metric classes + registry helpers if useful)
- `/workspace/shared/textual_features/tests/test_length_metrics.py` (only if fixture literals need correction after capture)
- `/workspace/shared/textual_features/tests/test_readability_metrics.py` (same)
- `/workspace/shared/textual_features/tests/test_registry.py` (add build()/name assertions for deterministic entries if not already present)

## Files forbidden to change

- `/workspace/shared/textual_features/valence.py`
- `/workspace/shared/textual_features/intergroup.py`
- `/workspace/shared/textual_features/prime.py`
- `/workspace/shared/textual_features/base.py` (contract frozen in Step 1)
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/**`
- `/workspace/experiments/predict_keep_remove_2026_05_07/**`
- `/workspace/pyproject.toml` (spaCy already available via `dev` group; do not add packages)

## Implementation rules (parity)

1. Copy formulas and regexes from the experiment sources—do not “improve” tokenization.
2. Readability must keep spaCy `blank("en")` + `sentencizer` and the same syllable heuristic as `_count_syllables` / `_readability_counts` in the experiment file.
3. Empty-string and zero-denominator behavior must match `safe_divide` (return `0.0`).
4. Metric `.name` strings must remain exactly: `char_count`, `word_count`, `sentence_count`, `avg_sentence_length`, `punctuation_count`, `punctuation_density`, `flesch_kincaid_grade`, `flesch_reading_ease`.
5. Prefer shared helpers in `text_utils.py` over duplicating regexes across metric files.

## Dependency order (flesh one at a time)

1. `text_utils.py` helpers
2. `char_count.py` → `word_count.py` → `sentence_count.py` → `avg_sentence_length.py` → `punctuation_count.py` → `punctuation_density.py`
3. `flesch_kincaid_grade.py` + `reading_ease.py` (shared readability counts)
4. Registry `build` wiring for the eight deterministic names
5. Confirm tests green

## Exact commands

```bash
cd /workspace

# Need spaCy for readability (dev group)
uv sync

PYTHONPATH=. uv run pytest shared/textual_features/tests/test_length_metrics.py -q
# Expected: PASS

PYTHONPATH=. uv run pytest shared/textual_features/tests/test_readability_metrics.py -q
# Expected: PASS

PYTHONPATH=. uv run pytest shared/textual_features/tests/test_registry.py -q
# Expected: PASS for deterministic entries; classifier stubs may still NotImplemented

# Cross-check vs experiment classes on the fixture string
PYTHONPATH=. uv run python - <<'PY'
from shared.textual_features.registry import (
    CHAR_COUNT, WORD_COUNT, SENTENCE_COUNT, AVG_SENTENCE_LENGTH,
    PUNCTUATION_COUNT, PUNCTUATION_DENSITY, FLESCH_KINCAID_GRADE, READING_EASE,
    get_feature,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.length_compression_analysis.metrics import (
    DEFAULT_LENGTH_METRICS,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.readability_complexity_analysis.metrics import (
    DEFAULT_READABILITY_METRICS,
)
text = "Hello world!"
legacy = {m.name: m.calculate(text) for m in DEFAULT_LENGTH_METRICS}
shared_names = [
    CHAR_COUNT, WORD_COUNT, SENTENCE_COUNT, AVG_SENTENCE_LENGTH,
    PUNCTUATION_COUNT, PUNCTUATION_DENSITY,
]
for key in shared_names:
    m = get_feature(key).build()
    assert m.calculate(text) == legacy[m.name], (key, m.calculate(text), legacy[m.name])
text2 = "Hello world."
legacy_r = {m.name: m.calculate(text2) for m in DEFAULT_READABILITY_METRICS}
for key in (FLESCH_KINCAID_GRADE, READING_EASE):
    m = get_feature(key).build()
    assert m.calculate(text2) == legacy_r[m.name], (key, m.calculate(text2), legacy_r[m.name])
print("PARITY_OK")
PY
```

**Expected stdout ends with:** `PARITY_OK`

## Pass / fail for this step

**Pass when:**
1. All length and readability unit tests pass.
2. Cross-check script prints `PARITY_OK` against still-unmigrated experiment classes.
3. `get_feature` builds working metrics for all eight deterministic registry names.
4. Classifier modules remain stubs.

**Fail when:** formulas diverge from experiment sources; tests pass only after changing fixtures to match a new formula; experiment files are edited; classifiers are implemented here.
