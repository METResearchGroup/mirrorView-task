# Step 1: Commit the plan and the three existing smoke files

## Scope

- **Caller:** git staging of two explicit path prefixes on branch `cursor/epic-218-226-generate-is-structurally-complete-d983`, then the stacked pull request opened with `gh stack submit`.
- **Task:** Commit this one-PR plan and the three existing `is_structurally_complete` smoke files. Do not change product Python. Do not rerun the smoke. Do not run the 400000-row job.
- **Out of scope:** Sibling smoke directories, `parent_cost_aggregate.json`, product code, pytest, changelog (after the pull request exists), parent issue 218 edits, Phase B production labeling.

## Files to inspect

- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_cost_report.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_resume_evidence.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_s3_checks.txt`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json`
- `CHANGELOG.md` (read only until the pull request exists)

## Files allowed to change

- `docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/plan.md` (new)
- `docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/steps/step1.md` (new)
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_cost_report.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_resume_evidence.json`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_s3_checks.txt`

## Files forbidden to change

- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_likely_spam/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_political/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_self_contained/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/llm_toxicity_tiered/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/political_stance/**`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/parent_cost_aggregate.json`
- Any file under `data_platform/`
- Any file under `lib/`
- Any file under `tests/`
- `CHANGELOG.md` (until after the pull request exists)
- GitHub issue 218

Stage files by explicit path only. Never run `git add -A` or `git add .`.

## Locked identities

| Field | Value |
| ----- | ----- |
| Feature | `is_structurally_complete` |
| Smoke rows | `10` |
| First id | `t1_mpxmfe6` |
| Engine | `bedrock` |
| Model | `us.amazon.nova-micro-v1:0` |
| Concurrency | 1 process x 8 threads |
| `estimated_full_run_usd_avg` | `7.1974` |
| `estimated_full_run_usd_max` | `9.394` |
| Full-run row count | `400000` |
| `resume_ok` | `true` |
| `reattached_same_batch_id` | `true` |
| Primary smoke prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/smoke/` |

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

1. Confirm the three smoke files already match the locked identities.
2. Commit `docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/` first.
3. Commit the three `is_structurally_complete` smoke files second.
4. Confirm other untracked smoke directories remain untracked.

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
cost = json.loads((base / "is_structurally_complete" / "is_structurally_complete_cost_report.json").read_text())
resume = json.loads((base / "is_structurally_complete" / "is_structurally_complete_resume_evidence.json").read_text())
shared = json.loads((base / "deterministic_ten_comment_ids.json").read_text())
checks = (base / "is_structurally_complete" / "is_structurally_complete_s3_checks.txt").read_text()
assert cost["feature"] == "is_structurally_complete"
assert cost["engine_type"] == "bedrock"
assert cost["model"] == "us.amazon.nova-micro-v1:0"
assert cost["request_count"] == 10
assert cost["source_record_ids"] == ids
assert cost["source_record_ids"][0] == "t1_mpxmfe6"
assert cost["estimated_full_run_usd_avg"] == 7.1974
assert cost["estimated_full_run_usd_max"] == 9.394
assert cost["full_run_row_count"] == 400000
assert cost["smoke_uri"].endswith("is_structurally_complete/smoke/")
assert resume["resume_ok"] is True
assert resume["reattached_same_batch_id"] is True
assert resume["rows_written"] == 10
assert resume["submit_calls_after_resume"]["converse"] == 0
assert shared["source_record_ids"] == ids
assert "no_batches_prefix_objects=true" in checks
assert "output_rows=10" in checks
assert "objects=0" in checks
print("smoke_artifacts_ok")
PY
```

Expected: `smoke_artifacts_ok`.

```bash
git add docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/
git diff --cached --name-only
```

Expected:

```text
docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/plan.md
docs/plans/2026-09-07_reddit_is_structurally_complete_smoke_778abc/steps/step1.md
```

```bash
git add docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/
git diff --cached --name-only
```

Expected:

```text
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_cost_report.json
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_resume_evidence.json
docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_s3_checks.txt
```

After both commits:

```bash
git status --porcelain
```

Expected: the other two feature smoke directories and `parent_cost_aggregate.json` remain `??`. No `data_platform/` or `tests/` paths.

## Must fail

- Staging any sibling smoke directory or `parent_cost_aggregate.json`.
- Editing any file under `data_platform/`, `lib/`, or `tests/`.
- Running pytest.
- Running the 400000-row production command.
- Using a closing GitHub keyword on issue 218.

## Done when

The branch has the plan commit and the three-file smoke commit. Other untracked report directories are still untracked. Product Python is unchanged.
