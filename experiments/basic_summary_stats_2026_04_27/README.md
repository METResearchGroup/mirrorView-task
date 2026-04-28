# Summary stats

Runs summary stats on the pilot run.

To refresh:

- Run `scripts/export_study_results.py` to get the latest data.
- Run `experiments/basic_summary_stats_2026_04_27/summary_stats.py` to get the latest stats.
- Run `experiments/basic_summary_stats_2026_04_27/total_attrition.py` to get an attrition analysis.

There may be a divergence in the counts between summary_stats.py and total_attrition.py during the course of the study, e.g., 

```bash
(mirrorview-task) (base) ➜  mirrorView-task git:(add-initial-pilot-analysis) ✗ PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/summary_stats.py
Copied mirrorview_pilot_data_2026_04_27-22:10:13.csv -> /Users/mark/Documents/work/mirrorView-task/experiments/basic_summary_stats_2026_04_27/latest_mirrorview_pilot_data.csv (canonical name for this run)
Loaded 27,266 rows, 832 distinct prolific_id(s)

Table 1 - Users by political party x condition
condition    control  training  training-assisted  total
party_group                                             
democrat         190       183                182    555
republican        99        85                 93    277
total            289       268                275    832

Table 2 - Phase 1 keep/remove (counts + proportion of each within party x condition)
decision                      keep  remove  total  prop_keep  prop_remove
democrat   control            1276     624   1900     0.6716       0.3284
           training           1242     598   1840     0.6750       0.3250
           training-assisted  1267     573   1840     0.6886       0.3114
republican control             636     354    990     0.6424       0.3576
           training            581     269    850     0.6835       0.3165
           training-assisted   585     345    930     0.6290       0.3710

Table 3 - Phase 2 keep/remove (counts + proportion of each within party x condition)
decision                      keep  remove  total  prop_keep  prop_remove
democrat   control            1356     544   1900     0.7137       0.2863
           training           1284     556   1840     0.6978       0.3022
           training-assisted  1297     543   1840     0.7049       0.2951
republican control             689     301    990     0.6960       0.3040
           training            600     250    850     0.7059       0.2941
           training-assisted   635     295    930     0.6828       0.3172
```

While for attrition:

```bash
(mirrorview-task) (base) ➜  mirrorView-task git:(add-initial-pilot-analysis) ✗ PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/total_attrition.py
Latest export: /Users/mark/Documents/work/mirrorView-task/scripts/mirrorview_pilot_data_2026_04_27-22:10:13.csv
Export timestamp: 2026_04_27-22:10:13
Eligibility cutoff: assigned before 2026_04_27-21:50:13 (20 minute grace period)
Exported valid unique prolific_id(s): 832
Eligible assigned user(s): 977
Eligible assigned user(s) found in export: 752
Eligible assigned user(s) missing from export: 225

Attrition by political party x condition
                              assigned_eligible  found_in_export  missing_from_export  attrition_rate
democrat   control                          205              168                   37          0.1805
           training                         205              165                   40          0.1951
           training-assisted                205              164                   41          0.2000
republican control                          121               87                   34          0.2810
           training                         121               82                   39          0.3223
           training-assisted                120               86                   34          0.2833
```

summary_stats.py now counts all users present in the latest exported CSV, grouped by prolific_id, so if summary_stats.py reports ~764, that means: 764 unique Prolific IDs are already in the CSV.

total_attrition.py’s found_in_export is narrower. It first restricts DynamoDB assignments to users assigned before export timestamp minus 20 minutes, then asks which of those eligible assigned users are in the export.

summary_stats total ≈ all exported users
total_attrition found_in_export = exported users assigned before the 20-min grace period cutoff (to avoid users that are doing the experiment in real time).

If summary_stats.py is larger than total_attrition.py’s found_in_export, the difference is users who finished and were saved in the export, but whose assignment happened after the cutoff.
