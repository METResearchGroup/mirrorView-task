# Step 4: Migrate mirrors content analysis to the shared package

## Goal

Delete duplicated formulas/prompts from the mirrors analysis metric and classifier modules. Make those files thin wrappers that import from `shared.textual_features` while preserving public names used by `main.py`, aggregators, and label CSV exporters. Keep on-disk label CSV paths and keep/remove join paths unchanged.

## Caller / unit of work

**Main callers (this step):**

1. `LengthCompressionAnalyzer` / `ReadabilityComplexityAnalyzer` constructing `DEFAULT_*_METRICS` from experiment `metrics.py`.
2. Experiment `classifier.py` `classify_post` / `classify_texts` / `classify_posts` used by `__main__` and any direct imports.
3. `experiments/mirrors_content_analysis_2026_04_24/analysis/interfaces.py` consumers importing `CalculateMetric`.

**Slice:** experiment modules re-export shared implementations; local formula/prompt bodies removed.

**Out of scope:** changing aggregator/renderer logic; regenerating `labels_*.csv`; editing `predict_keep_remove_2026_05_07/dataloader.py` join directories; renaming feature columns.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/textual_features/char_count.py` (and siblings) | Import targets |
| `/workspace/shared/textual_features/valence.py` (and intergroup/prime) | Import targets |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/main.py` | Imports `DEFAULT_LENGTH_METRICS`, `CalculateMetric` |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/main.py` | Imports `DEFAULT_READABILITY_METRICS` |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/metric_aggregator.py` | Uses metric protocol / `metrics_dict_for_text` |
| `/workspace/experiments/predict_keep_remove_2026_05_07/dataloader.py` | Confirms label dirs stay under experiment analysis paths |

## Files allowed to change

- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/interfaces.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/metrics.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/metrics.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/valence_classifier/classifier.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/intergroup_classifier/classifier.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py`

## Files forbidden to change

- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/main.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/main.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/metric_aggregator.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/table_renderer.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/analysis_utils.py` (still used by aggregator party/condition helpers)
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/link_mirrorview_run_to_labels.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/main.py` for classifiers
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/labels_*.csv`
- `/workspace/experiments/predict_keep_remove_2026_05_07/**`
- `/workspace/shared/textual_features/**` (behavior frozen; only import from it)

## Per-file changes (exact)

### 1. `analysis/interfaces.py`

Replace the local ABC body with:

```text
from shared.textual_features.base import CalculateMetric
__all__ = ["CalculateMetric"]
```

(or equivalent re-export). Do not keep a second ABC definition.

### 2. `length_compression_analysis/metrics.py`

- Remove local class bodies and regex imports from `analysis_utils` used only for metrics.
- Import `CharCountMetric`, `WordCountMetric`, `SentenceCountMetric`, `AvgSentenceLengthMetric`, `PunctuationCountMetric`, `PunctuationDensityMetric` from the matching `shared.textual_features.*` modules.
- Keep `DEFAULT_LENGTH_METRICS` tuple with the same order and class names as today.

### 3. `readability_complexity_analysis/metrics.py`

- Remove local spaCy/syllable helpers and class bodies.
- Import `FleschKincaidGradeMetric` from `shared.textual_features.flesch_kincaid_grade` and `FleschReadingEaseMetric` from `shared.textual_features.reading_ease`.
- Keep `DEFAULT_READABILITY_METRICS` order identical.

### 4. `valence_classifier/classifier.py`

- Remove local prompt strings, `ValenceClassification`, `get_llm`, `classify_post`, `classify_texts` implementations.
- Re-export those symbols from `shared.textual_features.valence`.
- **Keep** experiment-local: `VALENCE_CLASSIFIER_DIR`, label paths, `_all_mirrors_claude_path`, `_build_posts_frame`, `_label_posts_dataframe`, `classify_posts`, and `if __name__ == "__main__"`.
- `classify_posts` must call the shared `classify_texts` (via re-export) so labeling still works.

### 5. `intergroup_classifier/classifier.py` and `prime_classifier/classifier.py`

Same pattern as valence: shared classify API re-exported; CSV batch helpers remain local.

## Exact commands

```bash
cd /workspace

# Metrics still construct and match shared
PYTHONPATH=. uv run python - <<'PY'
from experiments.mirrors_content_analysis_2026_04_24.analysis.length_compression_analysis.metrics import (
    DEFAULT_LENGTH_METRICS, CharCountMetric,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.readability_complexity_analysis.metrics import (
    DEFAULT_READABILITY_METRICS,
)
from shared.textual_features.char_count import CharCountMetric as SharedChar
from shared.textual_features.registry import CHAR_COUNT, get_feature

assert CharCountMetric is SharedChar or CharCountMetric().name == SharedChar().name
text = "Hello world!"
assert DEFAULT_LENGTH_METRICS[0].calculate(text) == get_feature(CHAR_COUNT).build().calculate(text)
assert DEFAULT_READABILITY_METRICS[0].name == "flesch_kincaid_grade"
print("METRICS_REEXPORT_OK")
PY

# Classifier re-exports resolve; CSV helpers still local
PYTHONPATH=. uv run python - <<'PY'
from experiments.mirrors_content_analysis_2026_04_24.analysis.valence_classifier import classifier as v
from experiments.mirrors_content_analysis_2026_04_24.analysis.intergroup_classifier import classifier as i
from experiments.mirrors_content_analysis_2026_04_24.analysis.prime_classifier import classifier as p
from shared.textual_features import valence, intergroup, prime

assert v.classify_post is valence.classify_post or callable(v.classify_post)
assert i.classify_post is intergroup.classify_post or callable(i.classify_post)
assert p.classify_post is prime.classify_post or callable(p.classify_post)
assert callable(v.classify_posts) and hasattr(v, "LABELS_ORIGINAL_PATH")
assert callable(i.classify_posts) and hasattr(i, "LABELS_ORIGINAL_PATH")
assert callable(p.classify_posts) and hasattr(p, "LABELS_ORIGINAL_PATH")
print("CLASSIFIER_REEXPORT_OK")
PY

# Ensure experiment metrics.py files no longer contain formula bodies
rg -n "float\\(len\\(text\\)\\)|Flesch-Kincaid Grade Level|PRIME_SYSTEM_PROMPT|BINARY_SENTIMENT_PROMPT|INTERGROUP_SYSTEM_PROMPT" \
  experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/metrics.py \
  experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis/metrics.py \
  experiments/mirrors_content_analysis_2026_04_24/analysis/valence_classifier/classifier.py \
  experiments/mirrors_content_analysis_2026_04_24/analysis/intergroup_classifier/classifier.py \
  experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py \
  && echo "UNEXPECTED_LOCAL_BODIES" && exit 1 || echo "NO_LOCAL_BODIES"
```

**Expected:**
- `METRICS_REEXPORT_OK`
- `CLASSIFIER_REEXPORT_OK`
- `NO_LOCAL_BODIES`

## Pass / fail for this step

**Pass when:**
1. Experiment `metrics.py` / classifier classify helpers are thin re-exports of shared code.
2. `DEFAULT_LENGTH_METRICS` / `DEFAULT_READABILITY_METRICS` still importable with identical names/order.
3. Classifier CSV batch helpers and label paths remain under the experiment packages.
4. No changes to keep/remove dataloader paths or label CSV contents.
5. `rg` check reports `NO_LOCAL_BODIES`.

**Fail when:** aggregator/main files are edited “for convenience”; label CSVs regenerated; prompts left duplicated in experiment classifiers; shared package is redesigned during migration.
