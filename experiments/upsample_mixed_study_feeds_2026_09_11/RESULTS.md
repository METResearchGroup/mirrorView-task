# Upsample mixed study feeds, results

## Tests

`PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q` exited 0.

## Counts

| Count | Value |
| ----- | ----: |
| Base users | 3879 |
| Mixed source | 3202 |
| Cloned feeds | 1000 |
| User count | 4879 |
| Democrat rows | 2440 |
| Republican rows | 2439 |
| Democrat leftover-left | 339 |
| Republican leftover-left | 338 |
| Assignment slots | 97580 |

Source SHA-256: `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce`

Overprovisioned object: `s3://mirrorview-experimental-artifacts/experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments_overprovisioned.csv`

CSV SHA-256: `45b5cc0736a17a9be5a10f40dd49d4ae961bc383aa16591c89a185d2eaa98dd6`

The live prefix `2026_09_09-23:06:02` was left in place. DynamoDB production counters were not reset. The lookup Lambda was not changed.
