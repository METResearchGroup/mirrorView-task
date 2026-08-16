# Step 5: Join stated rule groups to disagreements

## Goal

Join mined free-response decision-rule clusters to raters and test whether disagreement concentrates in pairs of raters from different rule groups. Also compare empirical remove rates across rule groups.

## Caller / unit of work

Main caller:

```text
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e4_rule_groups.py
```

Flow: load the latest timestamped HDBSCAN assignment JSON under `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/{high,low}/`, map each `participant_id` to one rule-group label, join to trial and rater-effect tables, compute per-group severity, enumerate unordered disagreeing rater pairs on posts with three or more raters, compare the share of cross-group pairs among disagreeing pairs against a permutation baseline that shuffles rule labels within the same rater set, write summary tables.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/ambiguous_cases_2026_08_16/PROPOSAL.md` | E4 contract |
| `/workspace/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/` | Rule clusters |
| `/workspace/docs/study_updates/METHODS_WRITEUP_2026_08_13.md` | Theme names |

## Files allowed to change

- `/workspace/experiments/ambiguous_cases_2026_08_16/src/run_e4_rule_groups.py`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e4/rater_rule_groups.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e4/group_severity.csv`
- `/workspace/experiments/ambiguous_cases_2026_08_16/outputs/e4/summary.json`

## Files forbidden to change

- `/workspace/experiments/mine_free_response_for_features_2026_08_03/**`
- `/workspace/shared/**`

## Contracts to freeze

### Rater mapping

Use the latest directory under each of:

- `/workspace/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/high/`
- `/workspace/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/low/`

Read `assignments_hdbscan.json` from each. For each `participant_id`, take the modal non-noise `cluster_id` among that participant's feature rows (`cluster_id != -1`). The rule-group string is `{band}_cluster_{cluster_id}`, for example `high_cluster_3`. If every feature for the participant is noise or missing, label the participant `unassigned`. Unassigned raters are excluded from the cross-group pair test but retained in the mapping file.

### Cross-group test

Build all unordered pairs of distinct raters who both rated the same post and disagreed. Among pairs where both raters have assigned rule groups, compute the share whose rule groups differ. Compare that share to the mean share over 200 label-permutation draws with seed 42. Write `observed_cross_group_share`, `null_mean_cross_group_share`, and `null_p_greater` (share of null draws at least as large as observed).

### Outputs

`group_severity.csv` columns: `rule_group`, `n_raters`, `mean_empirical_remove_rate`, `mean_rater_effect`.

`summary.json` keys: `n_raters_assigned`, `n_raters_unassigned`, `observed_cross_group_share`, `null_mean_cross_group_share`, `null_p_greater`, `n_disagree_pairs_used`, `seed`.

## Exact commands

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e4_rule_groups.py
```

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
import pandas as pd
groups = pd.read_csv("experiments/ambiguous_cases_2026_08_16/outputs/e4/rater_rule_groups.csv")
summary = json.loads(Path("experiments/ambiguous_cases_2026_08_16/outputs/e4/summary.json").read_text())
assert "participant_id" in groups.columns
assert "rule_group" in groups.columns
assert "observed_cross_group_share" in summary
print("e4_ok", len(groups), round(summary["observed_cross_group_share"], 4))
PY
```

Expected shape:

```text
e4_ok <n_raters> <share>
```

## Pass / fail

Pass: mapping file exists, summary has observed and null shares, free-response outputs unchanged.

Fail: silent empty mapping, permutation not run, source mining outputs modified.

## Commit gate

Commit E4 script and outputs after `e4_ok` prints.
