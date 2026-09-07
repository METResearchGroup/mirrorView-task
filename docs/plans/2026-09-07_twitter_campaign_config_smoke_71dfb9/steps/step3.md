# Step 3: Add campaign mode to the Twitter feature generator

## Scope

- **Caller:** `data_platform.generate_features.generate_twitter_features.generate_twitter_features` and the existing Typer `main` from `build_feature_cli_main(TWITTER_SPEC, ...)`.
- **Task:** Add `campaign_id` and `preprocessed_run` to the Python API the same way `generate_bluesky_features()` does. The CLI already passes those flags through `platform_cli.py`.
- **Out of scope:** YAML loader, S3 migrate scripts, smoke, watcher, labeling 6,374 rows, writing production `batches/part-*.parquet` in this PR, pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/generate_bluesky_features.py` (campaign Python API to copy)
- `/workspace/data_platform/generate_features/generate_twitter_features.py` (missing `campaign_id` today)
- `/workspace/data_platform/generate_features/platform_cli.py` (`build_feature_cli_main` already has `--campaign-id` and `--preprocessed-run`; `generate_platform_campaign_feature` already passes `spec.platform`)

## Files allowed to change

- `/workspace/data_platform/generate_features/generate_twitter_features.py`

## Files forbidden to change

- `/workspace/data_platform/generate_features/platform_cli.py`
- `/workspace/data_platform/generate_features/generate_bluesky_features.py`
- `/workspace/data_platform/generate_features/registry.py`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Work

Match the campaign branch in `generate_bluesky_features()`.

1. Add optional `campaign_id: str | None = None` and `preprocessed_run: str | None = None` to `generate_twitter_features()`.
2. When either is not `None`, call `generate_platform_campaign_feature` with `TWITTER_SPEC` and return `{feature_name: prefix_uri}`.
3. When both are `None`, keep the existing `generate_platform_features` local-run path.
4. Update the module docstring with the campaign command:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

Do not run that production command in this pull request.

Return type becomes `dict[str, Path | str]` to match Bluesky.

Do not call `load_twitter_campaign_config` from this function. Campaign mode takes ids from the caller, matching Bluesky.

## Contracts (implement-from-spec Phase 3)

```python
def generate_twitter_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    checkpoint: str | None = None,
    campaign_id: str | None = None,
    preprocessed_run: str | None = None,
) -> dict[str, Path | str]:
```

Import `generate_platform_campaign_feature` from `platform_cli`.

## Given / when / then (Phase 4, no pytest)

```text
given generate_twitter_features.py after this step
when inspecting the signature of generate_twitter_features
then campaign_id and preprocessed_run exist as optional keyword arguments

given the Typer main from build_feature_cli_main
when the operator passes --campaign-id with --preprocessed-run
then the existing platform_cli campaign path runs with TWITTER_SPEC
and this PR does not execute a 6374-row production run
```

## Must pass

A runtime import check that the function accepts the campaign keywords:

```bash
PYTHONPATH=. uv run python -c "import inspect; from data_platform.generate_features.generate_twitter_features import generate_twitter_features; p=inspect.signature(generate_twitter_features).parameters; assert 'campaign_id' in p and 'preprocessed_run' in p; print('campaign kwargs ok')"
```

Expected: `campaign kwargs ok`

Do not run the production campaign command.

## Must fail

- Writing primary campaign `batches/part-*.parquet` in this PR
- Changing `platform_cli.py` or `FEATURE_REGISTRY`
- Adding pytest files

## Done when

`generate_twitter_features()` accepts `campaign_id` and `preprocessed_run` and delegates to `generate_platform_campaign_feature` the same way Bluesky does. No production feature run has been started.
