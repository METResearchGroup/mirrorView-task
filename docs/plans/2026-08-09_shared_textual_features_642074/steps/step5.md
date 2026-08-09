# Step 5: Run smoke checks for matching outputs and imports

## Goal

Show that the shared package is the source of truth, that migrated experiment wrappers still import cleanly, that registry coverage is complete, and that `experiments/predict_keep_remove_2026_05_07/dataloader.py` still points at the existing mirrors analysis label CSV directories (with no join-path rewrite).

## Caller / unit of work

**Main callers (this step):**

1. `pytest shared/textual_features/tests/`
2. Short `PYTHONPATH=. uv run python` smoke scripts in Exact commands
3. Import of `experiments.predict_keep_remove_2026_05_07.dataloader.Dataloader` path constants

**Out of scope:** re-running full mirrors analyses; calling OpenAI for corpus labeling; changing keep-or-remove model code; deleting legacy experiment files beyond Step 4's thinning.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/textual_features/registry.py` | Full catalog |
| `/workspace/experiments/predict_keep_remove_2026_05_07/dataloader.py` | `INTERGROUP_DIR`, `PRIME_DIR`, `VALENCE_DIR`, `LENGTH_DIR`, `READABILITY_DIR` |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/metrics.py` | Migrated wrapper |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/valence_classifier/classifier.py` | Migrated wrapper |

## Files allowed to change

- `/workspace/shared/textual_features/tests/test_registry.py` (only if adding a final completeness assertion that was missing earlier)
- `/workspace/docs/plans/2026-08-09_shared_textual_features_642074/plan.md` (optional note of completed verification; prefer leaving the plan stable)

No production code changes are expected in this step. If a smoke failure reveals a bug, fix it in the owning earlier step's allowed files and re-run this step.

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_2026_05_07/dataloader.py`
- `/workspace/experiments/predict_keep_remove_2026_05_07/models/**`
- Label CSV files under mirrors analysis
- Unrelated experiments

## Exact commands

```bash
cd /workspace

# 1) Unit tests
PYTHONPATH=. uv run pytest shared/textual_features/tests/ -q
# Expected: all PASS, exit 0

# 2) Registry completeness
PYTHONPATH=. uv run python - <<'PY'
from shared.textual_features import registry as r

required = [
    r.CHAR_COUNT, r.WORD_COUNT, r.SENTENCE_COUNT, r.AVG_SENTENCE_LENGTH,
    r.PUNCTUATION_COUNT, r.PUNCTUATION_DENSITY, r.FLESCH_KINCAID_GRADE,
    r.READING_EASE, r.VALENCE, r.INTERGROUP, r.PRIME,
]
missing = [n for n in required if n not in r.FEATURES]
assert not missing, missing
for n in required:
    entry = r.get_feature(n)
    if entry.kind == "metric":
        m = entry.build()
        assert m.calculate("Hello world!") >= 0.0
    else:
        assert callable(entry.classify_post)
print("REGISTRY_COMPLETE")
PY

# 3) Migrated experiment imports
PYTHONPATH=. uv run python - <<'PY'
from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric
from experiments.mirrors_content_analysis_2026_04_24.analysis.length_compression_analysis.metrics import (
    DEFAULT_LENGTH_METRICS,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.readability_complexity_analysis.metrics import (
    DEFAULT_READABILITY_METRICS,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.valence_classifier.classifier import (
    classify_post as valence_classify_post,
    classify_posts as valence_classify_posts,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.intergroup_classifier.classifier import (
    classify_post as intergroup_classify_post,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.prime_classifier.classifier import (
    classify_post as prime_classify_post,
)
from shared.textual_features.base import CalculateMetric as SharedABC

assert CalculateMetric is SharedABC
assert len(DEFAULT_LENGTH_METRICS) == 6
assert len(DEFAULT_READABILITY_METRICS) == 2
assert callable(valence_classify_post) and callable(valence_classify_posts)
assert callable(intergroup_classify_post) and callable(prime_classify_post)
print("EXPERIMENT_IMPORTS_OK")
PY

# 4) Keep/remove dataloader still joins experiment label dirs
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader

root = Path("experiments/mirrors_content_analysis_2026_04_24/analysis").resolve()
assert Dataloader.INTERGROUP_DIR == root / "intergroup_classifier"
assert Dataloader.PRIME_DIR == root / "prime_classifier"
assert Dataloader.VALENCE_DIR == root / "valence_classifier"
assert Dataloader.LENGTH_DIR == root / "length_compression_analysis"
assert Dataloader.READABILITY_DIR == root / "readability_complexity_analysis"
print("KEEP_REMOVE_PATHS_OK")
PY
```

**Expected stdout includes:**
- pytest all passed
- `REGISTRY_COMPLETE`
- `EXPERIMENT_IMPORTS_OK`
- `KEEP_REMOVE_PATHS_OK`

## Pass / fail for this step

**Pass when:**
1. All shared textual-features unit tests pass.
2. All 11 registry names resolve, metrics calculate, and classifiers expose `classify_post`.
3. Migrated experiment modules import without error, and `CalculateMetric` is the shared base class.
4. Keep-or-remove dataloader label directories remain under the mirrors analysis tree.
5. No production edits were required beyond fixes that belong to Steps 1 to 4.

**Fail when:** tests are skipped to force a green result; keep-or-remove paths are "fixed" by rewriting the dataloader; smoke requires regenerating label CSV files; OpenAI live calls are treated as required.
