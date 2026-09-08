# Step 2: Add the 2026-09-07 campaign YAML

## Scope

- **Caller:** `data_platform.generate_features.twitter_campaign_config.load_twitter_campaign_config` after Step 3. This step only adds the YAML file.
- **Task:** Add `mirrorview_2026-09-07_llm_features_v1.yaml` with identities from the preprocess child.
- **Out of scope:** Changing the loader in this step, editing the 2026-09-05 YAML, labeling, pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` (shape to copy. Do not edit.)
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/metadata.json`

## Files allowed to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml` (new)

## Files forbidden to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/twitter_campaign_config.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/curate/consolidate.py`
- Any file under `/workspace/tests/`
- Any file outside the allowed list for this pull request

## Locked contracts

Path:

```text
data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml
```

Required fields:

```yaml
campaign_id: twitter_2026_09_08_014808_llm_features_v1
platform: twitter
dataset_id: twitter_5901767a-e609-46fc-9a17-742516b548f2
preprocessed_run: "2026_09_08-01:48:08"
row_count: 6408
batch_size: 2000
engine_type: openai
model_id: gpt-5.4-nano
features:
  - is_news_or_opinion
  - is_political
  - is_likely_spam
  - is_self_contained
  - is_structurally_complete
  - political_stance
  - llm_toxicity_tiered
```

Do not reuse campaign id `twitter_2026_09_06_192847_llm_features_v1`. Do not use row count 6374.

## Given / when / then (Phase 4, no new pytest)

```text
given the new campaign YAML file
when the file is loaded as YAML
then campaign_id is twitter_2026_09_08_014808_llm_features_v1
and dataset_id is twitter_5901767a-e609-46fc-9a17-742516b548f2
and preprocessed_run is 2026_09_08-01:48:08
and row_count is 6408
and batch_size is 2000
and engine_type is openai
and model_id is gpt-5.4-nano
and features has seven names in the locked order
```

## Exact commands and expected output

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
import yaml
path = Path("data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml")
raw = yaml.safe_load(path.read_text())
assert raw["campaign_id"] == "twitter_2026_09_08_014808_llm_features_v1"
assert raw["dataset_id"] == "twitter_5901767a-e609-46fc-9a17-742516b548f2"
assert raw["preprocessed_run"] == "2026_09_08-01:48:08"
assert raw["row_count"] == 6408
assert raw["batch_size"] == 2000
assert raw["engine_type"] == "openai"
assert raw["model_id"] == "gpt-5.4-nano"
assert raw["features"] == [
    "is_news_or_opinion",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tiered",
]
print("yaml_ok", raw["campaign_id"], raw["row_count"])
PY
```

Expected: `yaml_ok twitter_2026_09_08_014808_llm_features_v1 6408`.

Do not add pytest.

## Pass / fail

The step passes when the new YAML exists with the locked identities and seven features in order, and the 2026-09-05 YAML is unchanged.

The step fails when any item below is true.

- 2026-09-05 YAML was edited
- row_count is 6374
- campaign id reuses `twitter_2026_09_06_192847_llm_features_v1`
- pytest was added
