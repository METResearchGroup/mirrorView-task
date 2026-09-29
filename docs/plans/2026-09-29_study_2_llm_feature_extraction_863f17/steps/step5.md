# Step 5: Name each cluster and ask for your review

Step 5 asks GPT-5.6 Terra to name each cluster from step 4, writes a review table, writes the draft feature list that step 6 labels against, and then stops for your feedback. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py`.

Out of scope are Jev calls and any change to the step 1 to step 4 code.

## Decisions

For each cluster, take its member features sorted by `feature_id`. When a cluster has more than 30 members, draw 30 without replacement with one `numpy.random.default_rng(SEED)`, and visit the clusters in `cluster_key` order so the draw is the same on every run. When a cluster has 30 or fewer members, use all of them. Show the kept text from step 3 for each sampled member.

Use `build_engine` and `run_batch` from `shared/llm.py`, so the model, the temperature, and the Batch API settings match step 2. The smoke test names the first 5 clusters in `cluster_key` order. The estimates use `total_requests` equal to the number of clusters, and they follow the same rules as step 2.

The prompt asks for a name of at most eight words. A longer name is kept. After the batch returns, any cluster whose name is empty after strip, or whose definition is empty after strip, is sent again in one new batch. That retry happens once. If a name or a definition is still empty, the step fails and lists those cluster keys.

The review table needs "the relative number of posts that have each feature", but no post has a label until step 6. So the table uses the share of the 320 batches whose features landed in the cluster as a stand-in, and it adds the share of the cluster's features that came from the kept side. The review table sorts rows by `n_batches` from high to low.

The feature list is a generated Python module, `shared/label_to_detail.py`, that holds one dictionary named `LABEL_TO_DETAIL`. Each key is `is_` plus the name in lowercase with every run of characters outside `a-z` and `0-9` replaced by one underscore, and with leading and trailing underscores stripped. When two names give the same key, the second one in `cluster_key` order gets `_2`, the third gets `_3`, and so on. Each value has two keys:

- `name`, the cluster name, which the charts use
- `description`, the one-sentence definition

`shared/constants.py` imports `LABEL_TO_DETAIL` from the module, so step 6 and step 7 read it from `shared/constants.py` as the issue asks. The mapping has no category.

## Prompt

`SYSTEM_PROMPT` in `src/step5_name_clusters/prompt.py` holds this text exactly:

```markdown
You are a computational linguistics analyst. A model read social-media post pairs from a keep/remove moderation task. Each pair is an original post and a mirror post that makes the same point from the opposite political side. The model listed features that set the kept pairs apart from the removed pairs, and similar features were then grouped into clusters.

You will see a sample of the features in one cluster.

Return a name for the cluster of at most eight words, and a definition of the cluster in one sentence. The name and the definition should describe what the features have in common, so that a reader can decide whether a new post pair has the feature.

Return as structured output.
```

`USER_TEMPLATE` holds this text, with `{feature_bullets}` as the only placeholder:

```markdown
## Features in the cluster

{feature_bullets}

Return the name and the definition.
```

`feature_bullets` is one line per sampled feature, each starting with `- `.

## Files to inspect

| Path | Why |
|------|-----|
| `docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/llm.py` | `build_feature_spec`, `build_engine`, `run_batch` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/estimates.py` | `build_estimates`, `require_estimates` |
| `shared/feature_discovery/llm_based/schemas.py` | The earlier `ClusterLabelResult`, which this step does not reuse because it asks the model for a cluster id and notes the issue did not request |

## Files allowed to change

All paths are under `experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section and the import of `LABEL_TO_DETAIL`
- Create `shared/label_to_detail.py`, only through `run.py --write-label-details` and then through your edits
- Create `src/step5_name_clusters/__init__.py`, `prompt.py`, `schemas.py`, `review.py`, `write_label_details.py`, and `run.py`
- Edit `SETUP.md` to add the step 5 commands, and edit `RESULTS.md` under `## Step 5: named features`

## Files forbidden to change

- `shared/**`
- `data_platform/**`
- Everything under `src/step1_setup/` to `src/step4_cluster_records/`

## Contracts

Add to `shared/constants.py`:

```text
CLUSTER_NAMING_SAMPLE_SIZE = 30
LABEL_KEY_PREFIX = "is_"
NAMING_SMOKE_KEY = "step5_name_clusters/smoke_cluster_names.jsonl"
NAMING_ESTIMATES_KEY = "step5_name_clusters/estimates.json"
CLUSTER_NAMES_KEY = "step5_name_clusters/cluster_names.jsonl"
FEATURE_REVIEW_KEY = "step5_name_clusters/feature_review.csv"
```

The import line goes at the end of `shared/constants.py`, and it is added in the same commit as the first generated `shared/label_to_detail.py`:

```text
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.label_to_detail import LABEL_TO_DETAIL
```

`src/step5_name_clusters/schemas.py`:

```text
ClusterName(BaseModel, extra="forbid"):
  name: str        Field(description="Name of the cluster, at most eight words.")
  definition: str  Field(description="One sentence that defines the cluster.")
ClusterNameRow(ClusterName):
  source_record_id: str, label_timestamp: str
```

`src/step5_name_clusters/prompt.py`:

```text
SYSTEM_PROMPT: str
USER_TEMPLATE: str
sample_cluster_features(assignments: pd.DataFrame, features: pd.DataFrame,
                        sample_size: int, seed: int) -> dict[str, list[str]]
  cluster_key -> sampled feature texts, following the Decisions section.
render_cluster_prompt(feature_texts: list[str]) -> str
build_naming_tasks(samples: dict[str, list[str]], sizes: pd.DataFrame) -> list[LabelTask]
  One task per cluster in cluster_key order, with uri = cluster_key.
```

`src/step5_name_clusters/review.py`:

```text
empty_cluster_keys(rows: list[dict]) -> list[str]
  cluster_key values whose name or definition is empty after strip.
build_feature_review(rows: list[dict], sizes: pd.DataFrame, total_batches: int) -> pd.DataFrame
  Columns cluster_key, name, definition, n_features, n_batches, batch_share,
  kept_share, sorted by n_batches descending and then cluster_key.
  batch_share = n_batches / total_batches. kept_share = n_kept_side / (n_kept_side + n_removed_side).
render_review_markdown(review: pd.DataFrame) -> str
  Shares as percentages with 1 decimal.
```

`src/step5_name_clusters/write_label_details.py`:

```text
label_key(name: str) -> str
build_label_to_detail(review: pd.DataFrame) -> dict[str, dict[str, str]]
  Keys follow the Decisions section, and collisions resolve in cluster_key order.
render_label_details_module(mapping: dict[str, dict[str, str]]) -> str
  A module docstring that names this step's run.py as the generator and says the file is
  reviewed by hand, then LABEL_TO_DETAIL: dict[str, dict[str, str]] = {...} with sorted keys.
validate_label_to_detail(mapping: dict[str, dict[str, str]]) -> None
  Raise ValueError when a key does not start with LABEL_KEY_PREFIX, a value does not have exactly
  the keys name and description, or a name or description is empty after strip.
```

`src/step5_name_clusters/run.py` takes exactly one of `--smoke`, `--full`, or `--write-label-details`.

- With `--smoke`, it names the first 5 clusters, writes and uploads the smoke rows and `NAMING_ESTIMATES_KEY`, and prints the table.
- With `--full`, it calls `require_estimates(NAMING_ESTIMATES_KEY)` and names every cluster. It then calls `empty_cluster_keys`. When that list is non-empty, it sends those clusters once more and replaces their rows. If any name or definition is still empty, it raises `ValueError` with those cluster keys. Otherwise it writes and uploads `CLUSTER_NAMES_KEY` and `FEATURE_REVIEW_KEY`, and prints the review Markdown.
- With `--write-label-details`, it reads the review, builds and validates the mapping, writes `shared/label_to_detail.py`, and prints `features=F`. It raises `FileExistsError` when `shared/label_to_detail.py` already exists, so a rerun cannot overwrite your edits.

## Commands

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --smoke
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --full
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --write-label-details
```

Paste the smoke table under `## Step 5: named features` in `RESULTS.md`. Then paste the review Markdown under it. The last command prints `features=F`, where `F` equals the step 4 cluster total.

## Stop for review

After the last command, the operator does these things in order:

1. Commit `shared/label_to_detail.py`, the `shared/constants.py` import, and `RESULTS.md`, then push and update the pull request.
2. Send you a message with the feature count and the review table. The message asks which features to drop, which to merge, which names or definitions to change, and whether the total count is right for step 6.
3. End the turn. Step 6 does not start in the same turn.

When you reply, the operator changes only `shared/label_to_detail.py`. To merge two features, keep one entry, rewrite its `name` and `description`, and delete the other entry. The operator then runs `validate_label_to_detail` on the edited mapping, writes the approved count and the approval date under `## Step 5: named features`, and commits.

## Pass

The full run reports no empty names or definitions, `features=F` matches the cluster count, and you have approved the feature list in writing.

## Fail

The step fails when step 6 starts before your approval, or when `shared/label_to_detail.py` fails `validate_label_to_detail`.
