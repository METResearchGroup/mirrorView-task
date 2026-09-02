# Step 4: Switch feature generation to full export names

## Goal

Feature specs carry a full export file name including the suffix. Feature load and write use a package-relative file path built from that name. Newly written `source_preprocessed_runs` values are package-relative directories.

## Caller / unit of work

**Main caller:** `generate_features` in `/workspace/data_platform/generate_features/generate_features.py` and `generate_platform_features` in `/workspace/data_platform/generate_features/platform_cli.py`.

**Slice:** construct feature storage with no records file name; append labels to `data/{platform}/{dataset_id}/features/{export_filename}`; skip ids already in that file; write feature-run metadata whose source-run list uses package-relative directories.

**Out of scope:** changing the feature registry's semantic names (`is_political`, and so on); slimming feature metadata; dual readers for old short source-run strings.

## Decision (locked)

Add `export_filename: str` to `FeatureSpec` in `/workspace/data_platform/generate_features/models.py`. Each registry entry sets it to the full csv name, e.g. `is_political.csv`. Do not restem from storage. Do not call `filename_for`.

Feature files live directly under the features stage root, not under a timestamped run directory. The package-relative file path is:

```text
data/{platform}/{dataset_id}/features/{export_filename}
```

Build that string with `to_package_relative(feature_storage.root_dir / spec.export_filename)` after the test fixture has pointed `PACKAGE_ROOT` at the temp dir, or by joining known parts. Prefer `to_package_relative` on the absolute file path under `root_dir` so the helper owns the POSIX shape.

`StorageManager(...)` construction in `platform_cli.py` and `generate_features.py` must drop `records_filename="features"` and `records_filename=feature_name`.

`FeatureLabelQuery.labeled_ids` loads from the package-relative path for that feature's `export_filename`. It may take `export_filename` instead of a stem, or look up the spec. Smallest change: `labeled_ids` / `filter_unlabeled` take the full file name (`is_political.csv`) OR keep taking the registry key and join `f"{feature_name}.csv"` only if every export name is `{name}.csv`. Lock the spec field and pass `spec.export_filename` so a later non-matching name still works.

`BaseBatchExecutionEngine.batch_write_records` must `append_records` to the feature file path, not `append_records(labels, feature_storage.root_dir)`.

`load_seen_uris_from_features_dir` must take or derive that same relative file path.

`resolve_source_preprocessed_runs` uses `to_package_relative` on each preprocessed run directory. Newly written values look like `data/bluesky/{id}/preprocessed/{timestamp}`.

When existing `features/metadata.json` is loaded, overwrite `source_preprocessed_runs` with the new shape (today already overwrites that field on load). Do not rewrite other historical files, and do not add a compatibility parser for the old short strings.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `FeatureGenerationConfig` |
| `/workspace/data_platform/generate_features/registry.py` | Every feature entry |
| `/workspace/data_platform/generate_features/generate_features.py` | Constructs StorageManager with records_filename |
| `/workspace/data_platform/generate_features/platform_cli.py` | Same |
| `/workspace/data_platform/generate_features/engines/base.py` | append_records to root_dir |
| `/workspace/data_platform/utils/feature_labels.py` | filename_for |
| `/workspace/data_platform/generate_features/metadata.py` | source_preprocessed_runs |
| `/workspace/tests/data_platform/generate_features/` | Constructors and metadata assertions |
| `/workspace/tests/data_platform/utils/test_feature_labels.py` | StorageManager records_filename |

## Files allowed to change

- `/workspace/data_platform/generate_features/models.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/generate_features.py`
- `/workspace/data_platform/generate_features/platform_cli.py`
- `/workspace/data_platform/generate_features/generate_bluesky_features.py` (only if it still uses the old storage API)
- `/workspace/data_platform/generate_features/generate_twitter_features.py` (same)
- `/workspace/data_platform/generate_features/generate_reddit_features.py` (same)
- `/workspace/data_platform/generate_features/engines/base.py`
- `/workspace/data_platform/generate_features/engines/langchain_engine.py` (only if it writes files)
- `/workspace/data_platform/generate_features/engines/thread_pool_engine.py` (same)
- `/workspace/data_platform/generate_features/metadata.py`
- `/workspace/data_platform/utils/feature_labels.py`
- `/workspace/tests/data_platform/generate_features/conftest.py`
- `/workspace/tests/data_platform/generate_features/test_generate_features.py`
- `/workspace/tests/data_platform/generate_features/test_generate_twitter_features.py`
- `/workspace/tests/data_platform/generate_features/test_generate_reddit_features.py`
- `/workspace/tests/data_platform/generate_features/test_generate_bluesky_features.py`
- `/workspace/tests/data_platform/generate_features/test_metadata.py`
- `/workspace/tests/data_platform/generate_features/test_platform_cli.py`
- `/workspace/tests/data_platform/utils/test_feature_labels.py`
- Other files under `/workspace/tests/data_platform/generate_features/` that fail on the new API

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/curate/**`
- Historical `features/metadata.json` on disk except the in-memory overwrite behavior that already exists when a run loads metadata

## Contracts to lock

```text
@dataclass(frozen=True)
class FeatureSpec:
  name: str
  model: type[BaseModel]
  engine_type: EngineType
  generate_fn: FeatureFn
  export_filename: str
  system_prompt: str | None = None
  llm_output_schema: type[BaseModel] | None = None

Registry examples:
  is_news_or_opinion -> export_filename="is_news_or_opinion.csv"
  is_political -> "is_political.csv"
  is_likely_spam -> "is_likely_spam.csv"
  is_self_contained -> "is_self_contained.csv"
  is_structurally_complete -> "is_structurally_complete.csv"
  is_toxic_tiered -> "is_toxic_tiered.csv"
  political_stance -> "political_stance.csv"

StorageManager(platform, StorageStage.FEATURES, model, dataset_id)
  No records_filename kwarg.

batch_write_records(..., feature_storage, relative_file_path: str) or close over spec.export_filename
  append_records(labels, package_relative_file_path)

FeatureLabelQuery.labeled_ids uses load_seen_ids_from_disk(package_relative_file_path, feature_file_id_column)

resolve_source_preprocessed_runs -> list[str] of to_package_relative(run_dir)
```

## Test design

given FeatureSpec without export_filename
when constructing a registry entry
then it is invalid (the field is required)

given a feature storage constructed without records_filename
when labels are appended
then the file is data/{platform}/{id}/features/is_political.csv (or the spec's export_filename)

given test_feature_labels
when labeled_ids is called
then it reads that csv through a package-relative path, not filename_for

given newly written feature metadata
then source_preprocessed_runs entries start with "data/" and include the platform and dataset id

Update `/workspace/tests/data_platform/generate_features/conftest.py` and `test_generate_twitter_features.py` so `StorageManager(...)` drops `records_filename`.

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 3 must add `export_filename` to `FeatureSpec` before rewriting registry entries.

Phase 5 units of work:

1. `FeatureSpec.export_filename` and registry values
2. `FeatureLabelQuery` package-relative load
3. Engine append path
4. `generate_features` / `platform_cli` constructors
5. `resolve_source_preprocessed_runs`
6. Feature tests green

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/generate_features tests/data_platform/utils/test_feature_labels.py tests/data_platform/preprocessing tests/data_platform/ingestion -q
```

Expected: exit 0.

## Must fail / not happen

- `StorageManager(..., records_filename=...)`.
- `filename_for` usage.
- Export names without a suffix (`is_political` as a file name).
- Dual readers for old `preprocessed/{timestamp}` source-run strings.
- Editing curated or ingest production files.
