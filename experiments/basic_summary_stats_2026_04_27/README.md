# Part 1 Full-Cohort Summary Statistics

## Summary

Reports participant counts, Phase 1 and Phase 2 keep/remove rates, and assignment-to-export attrition for MirrorView Study Phase 2 Part 1 (full ~2k cohort), broken down by political party × condition.

On the registered full export (2,003 unique Prolific IDs), keep rates are similar across conditions within party. Overall attrition is ~12% (273 / 2,276 eligible assigned), fairly even across party × condition cells (~10–14%).

## Purpose

Establish a descriptive read of the completed Part 1 cohort before modeling or causal analysis.

The experiment is intended to identify:

- How participants are distributed across party × condition cells
- Whether keep/remove rates differ by party or condition in Phase 1 vs Phase 2
- How much assignment-to-completion attrition exists, and whether it is uneven across cells

## Setup

- Dataset: `STUDY_PHASE_2_PART_1_RESULTS_FULL` via `shared.data.dataloader` → `shared/data/raw/study_phase_2_part_1/results/full.csv`
- Method: descriptive crosstabs and attrition accounting (no model)
- Conditions: `control`, `training`, `training-assisted`
- Party groups: `democrat`, `republican`
- Attrition eligibility: DynamoDB `user_assignments` for study `mirrorview` / iteration `pilot-phase2-v3`, assigned before dataset file mtime minus a 20-minute grace period
- Important fixed parameters: AWS region `us-east-2`; test/manual Prolific IDs excluded from attrition

## Flow

```text
load STUDY_PHASE_2_PART_1_RESULTS_FULL
→ tabulate party × condition and Phase 1/2 keep-remove rates
→ compare DynamoDB assignments (pilot-phase2-v3) to export
→ report attrition by party × condition
→ toxicity × party removal rates
```

## Run

From the repo root:

```bash
PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/summary_stats.py
PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/total_attrition.py
PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py
```

## Results

### Users by party × condition

| Party      | Control | Training | Training-assisted | Total |
| ---------- | ------: | -------: | ----------------: | ----: |
| Democrat   |     347 |      339 |               335 |  1021 |
| Republican |     335 |      321 |               326 |   982 |
| Total      |     682 |      660 |               661 |  2003 |

### Attrition (eligible assigned before grace cutoff)

| Party × condition              | Assigned eligible | Found in export | Missing | Attrition rate |
| ------------------------------ | ----------------: | --------------: | ------: | -------------: |
| Democrat / control             |               387 |             347 |      40 |         0.1034 |
| Democrat / training            |               387 |             339 |      48 |         0.1240 |
| Democrat / training-assisted   |               388 |             335 |      53 |         0.1366 |
| Republican / control           |               372 |             335 |      37 |         0.0995 |
| Republican / training          |               372 |             321 |      51 |         0.1371 |
| Republican / training-assisted |               370 |             326 |      44 |         0.1189 |

Eligible assigned: 2,276. Found in export: 2,003. Missing: 273.

Toxicity removal rates: [`toxicity_removal_by_party.md`](toxicity_removal_by_party.md).
