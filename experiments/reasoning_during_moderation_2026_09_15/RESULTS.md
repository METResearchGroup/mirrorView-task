# Reasoning tokens on split versus unanimous moderation posts

Export `since_date=2026-09-09`, `csv_files=3081`, `split=2201`, `unanimous_keep=2260`, `unanimous_remove=214`.

## Experiment 1

_No rows. GPU traces were not present in this environment._

## Experiment 2

_No rows. GPU traces were not present in this environment._

## Experiment 3

Values are milliseconds.

| level | group | n | mean | median | p25 | p75 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trial | split | 9882 | 18208.9115 | 12628.3000 | 7478.8000 | 21907.2250 | 511827.0000 |
| trial | unanimous_keep | 9671 | 19830.3415 | 13782.5000 | 7934.0000 | 23577.6000 | 861190.3000 |
| trial | unanimous_remove | 913 | 16894.5399 | 9982.0000 | 6075.9000 | 16228.1000 | 2183057.0000 |
| post_mean | split | 2201 | 18210.6089 | 14918.6750 | 10804.4750 | 21707.8400 | 170052.0600 |
| post_mean | unanimous_keep | 2260 | 19842.5570 | 16133.5175 | 11536.5062 | 23370.0688 | 223575.7500 |
| post_mean | unanimous_remove | 214 | 17082.7457 | 11758.5825 | 8366.0062 | 17526.7725 | 583608.0000 |

## Experiment 4

_No rows. GPU traces were not present in this environment._

Human `response_time_ms` is in the experiment 3 table. Thinking-token counts and marker rates were not measured, because this environment had no GPU traces. F1 and accuracy are out of scope.
