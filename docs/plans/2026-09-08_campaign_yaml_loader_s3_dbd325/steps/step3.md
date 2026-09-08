# Step 3: Scan the Twitter campaign YAML directory

## Scope

- **Caller:** `data_platform.generate_features.twitter_campaign_config.load_twitter_campaign_config`.
- **Task:** Scan `data_platform/generate_features/configs/twitter/*.yaml` for a mapping whose `campaign_id` matches. Remove the single-file campaign id lock.
- **Out of scope:** Changing smoke, generate, registry, watcher, curate, pytest, S3 upload.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/twitter_campaign_config.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` (calls the loader. Do not edit.)

## Files allowed to change

- `/workspace/data_platform/generate_features/twitter_campaign_config.py`

## Files forbidden to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/curate/consolidate.py`
- Any file under `/workspace/tests/`
- Any file outside the allowed list for this pull request

## Locked contracts

`load_twitter_campaign_config(campaign_id)`:

1. Iterate YAML files under `data_platform/generate_features/configs/twitter/`.
2. Load each mapping. If `campaign_id` matches, return it.
3. If two files match, raise `ValueError` naming the id.
4. If none match, raise `ValueError` whose message includes `unsupported twitter campaign id: {campaign_id}`.

Remove `ACCEPTED_CAMPAIGN_ID` and `CAMPAIGN_YAML_PATH`.

After this change:

- `load_twitter_campaign_config("twitter_2026_09_06_192847_llm_features_v1")` returns the 2026-09-05 YAML (`row_count` 6374).
- `load_twitter_campaign_config("twitter_2026_09_08_014808_llm_features_v1")` returns the 2026-09-07 YAML (`row_count` 6408).
- `load_twitter_campaign_config("bluesky_2026_09_03_235130_llm_features_v1")` raises and names that id.

## Given / when / then (Phase 4, no new pytest)

```text
given both Twitter campaign YAML files
when load_twitter_campaign_config("twitter_2026_09_08_014808_llm_features_v1")
then row_count is 6408, engine_type is openai, features length is 7,
     and dataset_id is twitter_5901767a-e609-46fc-9a17-742516b548f2

given both Twitter campaign YAML files
when load_twitter_campaign_config("twitter_2026_09_06_192847_llm_features_v1")
then row_count is 6374 and dataset_id is twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547

given both Twitter campaign YAML files
when load_twitter_campaign_config("bluesky_2026_09_03_235130_llm_features_v1")
then ValueError names unsupported twitter campaign id: bluesky_2026_09_03_235130_llm_features_v1
```

## Exact commands and expected output

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('twitter_2026_09_08_014808_llm_features_v1'); print(c['row_count'], c['engine_type'], len(c['features']), c['dataset_id'])"
```

Expected: `6408 openai 7 twitter_5901767a-e609-46fc-9a17-742516b548f2`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('twitter_2026_09_06_192847_llm_features_v1'); print(c['row_count'], c['dataset_id'])"
```

Expected: `6374 twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; load_twitter_campaign_config('bluesky_2026_09_03_235130_llm_features_v1')"
```

Expected: non-zero exit and `ValueError` naming `bluesky_2026_09_03_235130_llm_features_v1`.

Do not add pytest.

## Pass / fail

The step passes when both campaign ids load with the locked row counts and dataset ids, and an unknown id fails with that id in the message.

The step fails when any item below is true.

- loader still accepts only `twitter_2026_09_06_192847_llm_features_v1`
- 2026-09-05 YAML was edited or no longer loads
- unknown id error omits `unsupported twitter campaign id:`
- pytest was added
