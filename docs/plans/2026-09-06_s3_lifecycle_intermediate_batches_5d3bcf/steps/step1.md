# Step 1: Add the lifecycle JSON, the apply script, and the verify script, then apply and smoke in the lab bucket

## Goal

Install one enabled lifecycle rule on `mirrorview-experimental-artifacts` that expires objects 30 days after creation only when the key starts with `data_platform/data/` and the object carries tag `intermediate-artifact=true`. Commit the rule as JSON with an apply script that preserves other rules and a verify script that reads the bucket back.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step16.md`, and the tagging rules are in `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`. Every locked value below is copied from those two files. If this file disagrees with them, they win and this file is wrong.

## Main caller

`data_platform/infra/apply_data_platform_s3_lifecycle.py` `main`, run from the repo root.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python data_platform/infra/apply_data_platform_s3_lifecycle.py
```

Happy path through the caller: load the one rule from the committed JSON, read the current rules from the bucket (an absent configuration counts as no rules), keep every rule with a different id, replace or insert the named rule, put the merged list, and print one line naming the rule and bucket.

The second caller is `data_platform/infra/verify_data_platform_s3_lifecycle.py` `main`. It reads the bucket rules, finds the rule by id, compares status, prefix, tags, and expiration days with the committed JSON, and prints one `OK` or `FAIL` line.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step16.md` | Locked rule shape, commands, allowed and forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Which objects carry the tag (only `batches/part-*.parquet`) |
| `data_platform/generate_features/s3_feature_campaign.py` | `INTERMEDIATE_ARTIFACT_TAG` and how `Tagging` is applied on upload |
| `data_platform/scripts/verify_bluesky_s3_migration.py` | Script style to follow (module docstring with run command, `main`, `OK:` and `FAIL:` lines, `SystemExit(1)`) |
| `lib/aws/s3.py` | Region default `us-east-2` (read only, do not import into the infra scripts) |
| `AGENTS.md` | AWS credential export pattern |

## Files allowed to change

- `data_platform/infra/data_platform_s3_lifecycle.json` (new)
- `data_platform/infra/apply_data_platform_s3_lifecycle.py` (new)
- `data_platform/infra/verify_data_platform_s3_lifecycle.py` (new)
- `docs/plans/2026-09-06_s3_lifecycle_intermediate_batches_5d3bcf/**` (this plan)

No `__init__.py` is added under `data_platform/infra/`. `data_platform/scripts/` has none and its verify script imports from its sibling with `PYTHONPATH=.`.

## Files forbidden to change

- `CHANGELOG.md`
- `tests/**`
- `lib/aws/s3.py`, `data_platform/utils/object_store.py`, `data_platform/utils/storage.py`
- `data_platform/generate_features/**`
- Any Terraform file, IAM policy, or bucket versioning setting
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/**`

Stage files by explicit path only. Never run `git add -A` or `git add .`. The 24 Bluesky dump parquet files that `git status` lists as modified are an LFS artifact and are never staged.

## S3 rules for this step

- The only bucket configuration write is `put_bucket_lifecycle_configuration` with the merged rule list. No versioning, policy, or IAM call.
- The only object writes are the two smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/`.
- The only object deletes are those two smoke objects.
- Never tag an existing object. Never touch the 53 objects that Step 1 of the epic copied, and never touch any `features/` prefix.
- Stop and report before applying if the bucket already has a rule with id `expire-data-platform-intermediate-artifacts` whose content differs from the committed JSON, or any expiration rule on a `data_platform/` prefix. A read-only check before planning returned `NoSuchLifecycleConfiguration`, so no such rule exists today.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Rule id | `expire-data-platform-intermediate-artifacts` |
| Status | `Enabled` |
| Prefix filter | `data_platform/data/` |
| Tag filter | key `intermediate-artifact`, value `true` |
| Filter composition | `Filter.And` with both `Prefix` and `Tags` |
| Expiration | `Expiration.Days` = 30 |
| Config file | `data_platform/infra/data_platform_s3_lifecycle.json` |
| Smoke prefix | `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/` |
| Tagged smoke key | `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/tagged_batch.parquet` |
| Untagged smoke key | `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/final_feature.parquet` |
| Pinned untagged object | `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet` |

`data_platform_s3_lifecycle.json` must be exactly this document, with two-space indentation and a trailing newline:

```json
{
  "Rules": [
    {
      "ID": "expire-data-platform-intermediate-artifacts",
      "Status": "Enabled",
      "Filter": {
        "And": {
          "Prefix": "data_platform/data/",
          "Tags": [
            {
              "Key": "intermediate-artifact",
              "Value": "true"
            }
          ]
        }
      },
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

## Contracts

`data_platform/infra/apply_data_platform_s3_lifecycle.py`

| Name | Contract |
|------|----------|
| `BUCKET`, `REGION`, `RULE_ID` | The three locked strings above |
| `LIFECYCLE_PATH` | `Path(__file__).with_name("data_platform_s3_lifecycle.json")` |
| `load_rule() -> dict` | Returns the single rule from the JSON. Raises `ValueError` when the file does not hold exactly one rule with id `RULE_ID`. |
| `read_rules(client) -> list[dict]` | Returns the bucket's current rules. Returns `[]` when the bucket raises `NoSuchLifecycleConfiguration`. Any other `ClientError` propagates. |
| `merge_rule(existing: list[dict], rule: dict) -> list[dict]` | Returns a new list with every rule whose `ID` differs from `rule["ID"]` unchanged and in order. The named rule takes the position of the old rule with the same id, or is appended when there was none. |
| `main() -> None` | Runs the happy path, prints `existing rules: none` or `existing rules: <id>, <id>` before writing, then prints `applied lifecycle rule expire-data-platform-intermediate-artifacts on mirrorview-experimental-artifacts`. |

`data_platform/infra/verify_data_platform_s3_lifecycle.py`

| Name | Contract |
|------|----------|
| `find_rule(rules: list[dict], rule_id: str) -> dict \| None` | The rule with that id, or `None` |
| `rule_problems(installed: dict, expected: dict) -> list[str]` | One message per mismatch across `Status`, `Filter.And.Prefix`, `Filter.And.Tags`, and `Expiration.Days`. Empty when they match. |
| `main() -> None` | Reads the bucket rules (a missing configuration is one `FAIL`), finds the rule, compares against `load_rule()`, prints `OK: rule expire-data-platform-intermediate-artifacts prefix=data_platform/data/ tag=intermediate-artifact=true expiration_days=30` and exits 0, or prints one `FAIL: ...` line per problem and raises `SystemExit(1)`. |

The verify script imports `BUCKET`, `REGION`, `RULE_ID`, and `load_rule` from the apply script. Both scripts build `boto3.client("s3", region_name=REGION)` inside `main` and pass it down, so the merge and compare functions can be checked offline with plain dicts.

## Designed checks (no pytest)

The epic forbids new test files and forbids running pytest. Instead, each scenario below is run as a throwaway snippet from `/tmp` or as a live command, and the observed output is recorded in the PR description.

Offline scenarios for `merge_rule`:

```text
given existing == []
when merge_rule(existing, rule)
then the result is [rule]

given existing == [other_a, rule_old, other_b] where rule_old has RULE_ID and a different Expiration.Days
when merge_rule(existing, rule)
then the result is [other_a, rule, other_b] and existing is unchanged

given existing == [rule]
when merge_rule(existing, rule)
then the result is [rule] with length 1
```

Offline scenarios for `rule_problems`:

```text
given installed == expected
then rule_problems returns []

given installed with Expiration.Days 7
then rule_problems returns one message that mentions 7 and 30

given installed with Filter.And.Prefix data_platform/
then rule_problems returns one message that mentions the prefix
```

Offline scenario for `load_rule`:

```text
given the committed JSON
then load_rule()["ID"] == RULE_ID and load_rule()["Expiration"]["Days"] == 30
```

## Ordered implementation work

1. Write `data_platform/infra/data_platform_s3_lifecycle.json` verbatim from the block above. Commit.
2. Scaffold both scripts with module docstrings, constants, and stub bodies that raise `NotImplementedError`. Commit.
3. Fill in the signatures and docstrings from the Contracts table with stub bodies. Commit.
4. Write the offline check snippets from Designed checks to `/tmp/lifecycle_checks.py` and confirm they fail with `NotImplementedError`. Do not commit the snippet.
5. Implement `load_rule`, then `read_rules`, then `merge_rule`, then `apply` `main`, one commit each, rerunning the offline snippet after each.
6. Implement `find_rule`, then `rule_problems`, then `verify` `main`, one commit each.
7. Run the live commands below in order and record the output.

## Live commands and expected output

Every `aws` command in `step16.md` is replaced by a boto3 call here because the CLI is not installed. Run from `/workspace` with the credentials exported.

Identity:

```bash
PYTHONPATH=. uv run python -c "import boto3; print(boto3.client('sts', region_name='us-east-2').get_caller_identity()['Arn'])"
```

Expected: one IAM ARN line, exit 0.

Apply, twice:

```bash
PYTHONPATH=. uv run python data_platform/infra/apply_data_platform_s3_lifecycle.py
PYTHONPATH=. uv run python data_platform/infra/apply_data_platform_s3_lifecycle.py
```

Expected first run: `existing rules: none` then `applied lifecycle rule expire-data-platform-intermediate-artifacts on mirrorview-experimental-artifacts`. Expected second run: `existing rules: expire-data-platform-intermediate-artifacts` then the same applied line. Exit 0 both times.

Verify:

```bash
PYTHONPATH=. uv run python data_platform/infra/verify_data_platform_s3_lifecycle.py
```

Expected: `OK: rule expire-data-platform-intermediate-artifacts prefix=data_platform/data/ tag=intermediate-artifact=true expiration_days=30`, exit 0.

Cross-check the raw configuration:

```bash
PYTHONPATH=. uv run python -c "import boto3, json; print(json.dumps(boto3.client('s3', region_name='us-east-2').get_bucket_lifecycle_configuration(Bucket='mirrorview-experimental-artifacts')['Rules'], indent=2))"
```

Expected: a list with exactly one rule, equal to the committed JSON rule.

Smoke objects, tag read-back, and cleanup, in one snippet:

```python
import boto3
s3 = boto3.client("s3", region_name="us-east-2")
bucket = "mirrorview-experimental-artifacts"
prefix = "data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/"
tagged = prefix + "tagged_batch.parquet"
untagged = prefix + "final_feature.parquet"
s3.put_object(Bucket=bucket, Key=tagged, Body=b"smoke\n", Tagging="intermediate-artifact=true")
s3.put_object(Bucket=bucket, Key=untagged, Body=b"smoke\n")
print("tagged:", s3.get_object_tagging(Bucket=bucket, Key=tagged)["TagSet"])
print("untagged:", s3.get_object_tagging(Bucket=bucket, Key=untagged)["TagSet"])
deleted = s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": tagged}, {"Key": untagged}]})
print("deleted:", sorted(d["Key"] for d in deleted["Deleted"]))
print("remaining:", s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("KeyCount", 0))
```

Expected: `tagged: [{'Key': 'intermediate-artifact', 'Value': 'true'}]`, `untagged: []`, `deleted:` with both keys, `remaining: 0`.

Pinned object is untagged (read only):

```bash
PYTHONPATH=. uv run python -c "import boto3; print(boto3.client('s3', region_name='us-east-2').get_object_tagging(Bucket='mirrorview-experimental-artifacts', Key='data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet')['TagSet'])"
```

Expected: `[]`.

## Must pass

- The committed JSON matches the block above byte for byte apart from the trailing newline.
- Apply prints the applied line twice and the bucket holds exactly one rule after the second run.
- Verify prints the `OK` line and exits 0.
- The tagged smoke object reads back the tag, the untagged one reads back an empty set, and the smoke prefix is empty at the end.
- The pinned preprocessed object has an empty tag set.
- `git diff cursor/epic-180-187-progress-reports-watchers-d983...HEAD --stat` lists only files under `data_platform/infra/` and this plan folder.

## Must fail

- Verify exits 1 with a `FAIL` line if the rule is missing, disabled, has a different prefix, lacks the tag, or expires on a day count other than 30.
- `load_rule` raises `ValueError` if the JSON holds zero rules, two rules, or a rule with a different id.
