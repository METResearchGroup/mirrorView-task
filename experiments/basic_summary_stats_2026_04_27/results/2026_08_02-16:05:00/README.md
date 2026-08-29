# Results — 2026_08_02-16:05:00

Source: `STUDY_PHASE_2_PART_1_RESULTS_FULL` → `shared/data/raw/study_phase_2_part_1/results/full.csv`  
65,581 rows · 2,003 distinct `prolific_id`s  
Attrition study iteration: `pilot-phase2-v3` (20 min grace; cutoff from file mtime)

Scripts: `summary_stats.py`, `total_attrition.py`, `toxicity_remove_breakdown.py`  
Raw logs: `summary_stats.txt`, `total_attrition.txt`, `toxicity_remove_breakdown.txt`.

## Table 1 — Users by party × condition

| party_group | control | training | training-assisted | total |
|---|---:|---:|---:|---:|
| democrat | 347 | 339 | 335 | 1021 |
| republican | 335 | 321 | 326 | 982 |
| total | 682 | 660 | 661 | 2003 |

## Table 2 — Phase 1 keep/remove

| party × condition | keep | remove | total | prop_keep | prop_remove |
|---|---:|---:|---:|---:|---:|
| democrat / control | 2317 | 1153 | 3470 | 0.6677 | 0.3323 |
| democrat / training | 2275 | 1125 | 3400 | 0.6691 | 0.3309 |
| democrat / training-assisted | 2311 | 1059 | 3370 | 0.6858 | 0.3142 |
| republican / control | 2159 | 1201 | 3360 | 0.6426 | 0.3574 |
| republican / training | 2127 | 1093 | 3220 | 0.6606 | 0.3394 |
| republican / training-assisted | 2053 | 1207 | 3260 | 0.6298 | 0.3702 |

## Table 3 — Phase 2 keep/remove

| party × condition | keep | remove | total | prop_keep | prop_remove |
|---|---:|---:|---:|---:|---:|
| democrat / control | 2481 | 989 | 3470 | 0.7150 | 0.2850 |
| democrat / training | 2351 | 1049 | 3400 | 0.6915 | 0.3085 |
| democrat / training-assisted | 2336 | 1034 | 3370 | 0.6932 | 0.3068 |
| republican / control | 2308 | 1052 | 3360 | 0.6869 | 0.3131 |
| republican / training | 2243 | 977 | 3220 | 0.6966 | 0.3034 |
| republican / training-assisted | 2217 | 1043 | 3260 | 0.6801 | 0.3199 |

## Attrition (assignment → export)

Eligibility cutoff: assigned before `2026_08_01-08:10:11` (file mtime of `full.csv` minus 20 min).  
Eligible assigned: 2,276 · found in export: 2,003 · missing: 273

| party × condition | assigned_eligible | found_in_export | missing | attrition_rate |
|---|---:|---:|---:|---:|
| democrat / control | 387 | 347 | 40 | 0.1034 |
| democrat / training | 387 | 339 | 48 | 0.1240 |
| democrat / training-assisted | 388 | 335 | 53 | 0.1366 |
| republican / control | 372 | 335 | 37 | 0.0995 |
| republican / training | 372 | 321 | 51 | 0.1371 |
| republican / training-assisted | 370 | 326 | 44 | 0.1189 |

`summary_stats` counts all exported users (2,003). Attrition `found_in_export` matches that total here because the study is complete and the grace cutoff is after collection ended.

## Removal by party × sampled toxicity

Moderation trials, phases 1–2 (40,160 rows). Pipeline does not drop `sample_middle_toxicity`.

| sample_toxicity_type | democrat prop_remove | republican prop_remove | dem n | rep n |
|---|---:|---:|---:|---:|
| sample_low_toxicity | 0.1648 | 0.1785 | 5120 | 4920 |
| sample_middle_toxicity | 0.2825 | 0.3027 | 10240 | 9840 |
| sample_high_toxicity | 0.5219 | 0.5520 | 5120 | 4920 |
