# Step 1: Commit the plan, the three existing smoke files, and the parent aggregate

## Scope

- **Caller:** git staging of three explicit path prefixes on branch `cursor/epic-218-228-generate-llm-toxicity-tiered-d983`, then the stacked pull request opened with `gh stack submit`.
- **Task:** Commit this one-PR plan, the three existing `llm_toxicity_tiered` smoke files, and `parent_cost_aggregate.json`. Do not change product Python. Do not rerun the smoke. Do not run the 400000-row job.
- **Out of scope:** Sibling smoke directories, product code, pytest, changelog (after the pull request exists), parent issue 218 edits, issue 229, Phase B production labeling, Perspective API `is_toxic_tiered`.

## Files to inspect

- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_cost_report.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_resume_evidence.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_s3_checks.txt`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/parent_cost_aggregate.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json`
- `CHANGELOG.md` (read only until the pull request exists)

## Files allowed to change

- `docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/plan.md` (new)
- `docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/steps/step1.md` (new)
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_cost_report.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_resume_evidence.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_s3_checks.txt`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/parent_cost_aggregate.json`

## Files forbidden to change

- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_likely_spam/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_political/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_self_contained/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/political_stance/**`
- Any file under `data_platform/`
- Any file under `lib/`
- Any file under `tests/`
- `CHANGELOG.md` (until after the pull request exists)
- GitHub issue 218
- GitHub issue 229

Stage files by explicit path only. Never run `git add -A` or `git add .`.

## Locked identities

| Field | Value |
| ----- | ----- |
| Feature | `llm_toxicity_tiered` |
| Smoke rows | `10` |
| First id | `t1_mpxmfe6` |
| Engine | `openai` |
| Model | `gpt-5.4-nano` |
| Output column | `toxicity_tier` |
| `estimated_full_run_usd_avg` | `21.144` |
| `estimated_full_run_usd_max` | `27.34` |
| Full-run row count | `400000` |
| `resume_ok` | `true` |
| `reattached_same_batch_id` | `true` |
| Primary smoke prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/llm_toxicity_tiered/smoke/` |
| Parent features included | `7` |
| Parent OpenAI features | `4` |
| Parent Bedrock features | `3` |
| Parent `total_estimated_full_run_usd_avg` | `99.0182` |
| Parent `total_estimated_full_run_usd_max` | `130.366` |
| Parent OpenAI subtotal avg / max | `80.646` / `105.53` |
| Parent Bedrock subtotal avg / max | `18.3722` / `24.836` |
| Parent `total_smoke_cost_usd` | `0.002476` |

Ten shared ids:

- `t1_mpxmfe6`
- `t1_mpxmfoa`
- `t1_mpxmfr2`
- `t1_mpxmgbj`
- `t1_mpxmgxp`
- `t1_mpxmho3`
- `t1_mpxmjkx`
- `t1_mpxmk1u`
- `t1_mpxmkdo`
- `t1_mpxmlk4`

## Ordered units of work

1. Confirm the three smoke files and the parent aggregate already match the locked identities.
2. Commit `docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/` first.
3. Commit the three `llm_toxicity_tiered` smoke files and `parent_cost_aggregate.json` second.
4. Confirm the worktree has no leftover untracked smoke report files.

## Must pass

```bash
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path

base = Path("docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke")
ids = [
    "t1_mpxmfe6",
    "t1_mpxmfoa",
    "t1_mpxmfr2",
    "t1_mpxmgbj",
    "t1_mpxmgxp",
    "t1_mpxmho3",
    "t1_mpxmjkx",
    "t1_mpxmk1u",
    "t1_mpxmkdo",
    "t1_mpxmlk4",
]
cost = json.loads((base / "llm_toxicity_tiered" / "llm_toxicity_tiered_cost_report.json").read_text())
resume = json.loads((base / "llm_toxicity_tiered" / "llm_toxicity_tiered_resume_evidence.json").read_text())
shared = json.loads((base / "deterministic_ten_comment_ids.json").read_text())
agg = json.loads((base / "parent_cost_aggregate.json").read_text())
checks = (base / "llm_toxicity_tiered" / "llm_toxicity_tiered_s3_checks.txt").read_text()
assert cost["feature"] == "llm_toxicity_tiered"
assert cost["engine_type"] == "openai"
assert cost["model"] == "gpt-5.4-nano"
assert cost["request_count"] == 10
assert cost["source_record_ids"] == ids
assert cost["source_record_ids"][0] == "t1_mpxmfe6"
assert cost["estimated_full_run_usd_avg"] == 21.144
assert cost["estimated_full_run_usd_max"] == 27.34
assert cost["full_run_row_count"] == 400000
assert cost["smoke_uri"].endswith("llm_toxicity_tiered/smoke/")
assert resume["resume_ok"] is True
assert resume["reattached_same_batch_id"] is True
assert resume["rows_written"] == 10
assert resume["submit_calls_after_resume"]["files.create"] == 0
assert resume["submit_calls_after_resume"]["batches.create"] == 0
assert shared["source_record_ids"] == ids
assert "toxicity_tier" in checks
assert "is_toxic_tiered" not in checks
assert "no_batches_prefix_objects=true" in checks
assert "output_rows=10" in checks
assert "objects=0" in checks
assert agg["features_included"] == 7
assert agg["openai_features"] == 4
assert agg["bedrock_features"] == 3
assert agg["full_run_row_count"] == 400000
assert agg["total_estimated_full_run_usd_avg"] == 99.0182
assert agg["total_estimated_full_run_usd_max"] == 130.366
assert agg["openai_estimated_full_run_usd_avg"] == 80.646
assert agg["openai_estimated_full_run_usd_max"] == 105.53
assert agg["bedrock_estimated_full_run_usd_avg"] == 18.3722
assert agg["bedrock_estimated_full_run_usd_max"] == 24.836
assert agg["total_smoke_cost_usd"] == 0.002476
by_name = {row["feature"]: row for row in agg["features"]}
assert by_name["is_news_or_opinion"]["estimated_full_run_usd_avg"] == 18.224
assert by_name["is_news_or_opinion"]["estimated_full_run_usd_max"] == 24.42
assert by_name["is_news_or_opinion"]["engine_type"] == "openai"
assert by_name["is_political"]["estimated_full_run_usd_avg"] == 17.534
assert by_name["is_political"]["estimated_full_run_usd_max"] == 23.73
assert by_name["is_political"]["engine_type"] == "openai"
assert by_name["political_stance"]["estimated_full_run_usd_avg"] == 23.744
assert by_name["political_stance"]["estimated_full_run_usd_max"] == 30.04
assert by_name["political_stance"]["engine_type"] == "openai"
assert by_name["llm_toxicity_tiered"]["estimated_full_run_usd_avg"] == 21.144
assert by_name["llm_toxicity_tiered"]["estimated_full_run_usd_max"] == 27.34
assert by_name["llm_toxicity_tiered"]["engine_type"] == "openai"
assert by_name["is_likely_spam"]["estimated_full_run_usd_avg"] == 4.7334
assert by_name["is_likely_spam"]["estimated_full_run_usd_max"] == 6.804
assert by_name["is_likely_spam"]["engine_type"] == "bedrock"
assert by_name["is_self_contained"]["estimated_full_run_usd_avg"] == 6.4414
assert by_name["is_self_contained"]["estimated_full_run_usd_max"] == 8.638
assert by_name["is_self_contained"]["engine_type"] == "bedrock"
assert by_name["is_structurally_complete"]["estimated_full_run_usd_avg"] == 7.1974
assert by_name["is_structurally_complete"]["estimated_full_run_usd_max"] == 9.394
assert by_name["is_structurally_complete"]["engine_type"] == "bedrock"
print("smoke_artifacts_ok")
PY
```

Expected: `smoke_artifacts_ok`.

```bash
git add docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/
git diff --cached --name-only
```

Expected:

```text
docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/plan.md
docs/plans/2026-09-07_reddit_llm_toxicity_tiered_smoke_dcc272/steps/step1.md
```

```bash
git add docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/ docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/parent_cost_aggregate.json
git diff --cached --name-only
```

Expected:

```text
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_cost_report.json
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_resume_evidence.json
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_s3_checks.txt
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/parent_cost_aggregate.json
```

After both commits:

```bash
git status --porcelain
```

Expected: empty output. No `data_platform/` or `tests/` paths.

## Must fail

- Staging any sibling smoke directory.
- Editing any file under `data_platform/`, `lib/`, or `tests/`.
- Running pytest.
- Running the 400000-row production command.
- Using a closing GitHub keyword on issue 218.
- Editing GitHub issue 218.
- Starting issue 229.
- Writing `APPROVED.txt`.
- Treating a merged pull request as permission to run the 400000-row job.

## Done when

The branch has the plan commit and the four-file smoke-plus-aggregate commit. Product Python is unchanged. The worktree is clean of leftover smoke report files.
