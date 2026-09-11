# Study progress, September 2026 run

Snapshot 2026_09_11-20:21:31 UTC. Export 2026_09_11-20:21:30.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 1,957 |
| Finished | 1,874 |
| Saved files | 1,881 |
| Labels | 37,620 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 48.3% |
| Label progress | 48.5% |
| Missing from export | 83 |
| Missing after 20-minute grace | 76 |
| Attrition after grace | 3.9% |

Prolific has finished 1,874 of 3,879 feeds (48.3%). Prolific has assigned a larger share of Democrat slots (60.7% assigned vs 40.2% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 56.4% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,178 | 1,136 | 1,940 | 60.7% | 96.4% |
| Republican | 779 | 738 | 1,939 | 40.2% | 94.7% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 15,664 | 7,096 | 22,760 | 68.8% | 31.2% | 68.8% | 31.2% | 100 | 6 |
| Republican | 10,536 | 4,324 | 14,860 | 70.9% | 29.1% | 70.9% | 29.1% | 101 | 6 |
| All | 26,200 | 11,420 | 37,620 | 69.6% | 30.4% | 69.6% | 30.4% | 201 | 12 |

Per-user keep rate (all finished): mean 69.6%, median 70.0%, SD 21.5%.

Per-user remove rate (all finished): mean 30.4%, median 30.0%, SD 21.5%.

201 people kept every scored post. 12 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 4,554 | 14.4% |
| Democrat | Middle | 11,380 | 26.9% |
| Democrat | High | 6,826 | 49.5% |
| Republican | Low | 4,458 | 16.5% |
| Republican | Middle | 7,430 | 28.4% |
| Republican | High | 2,972 | 49.7% |

Pooled Democrat remove is 31.2% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 4,554 | 20.0% |
| Democrat | Middle | 11,380 | 50.0% |
| Democrat | High | 6,826 | 30.0% |
| Republican | Low | 4,458 | 30.0% |
| Republican | Middle | 7,430 | 50.0% |
| Republican | High | 2,972 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 11,380 | 31.7% |
| Democrat | Right | 11,380 | 30.6% |
| Republican | Left | 7,430 | 29.5% |
| Republican | Right | 7,430 | 28.7% |

## Attention

Pass rate 78.3% (1,467 passed, 407 failed).

Remove share among people who passed: 28.9%. Among people who failed: 35.6%.

172 of 201 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.9%. Democrat passers 29.8%. Republican passers 27.4%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,733 |
| Catalog posts | 18,899 |
| Posts with 1 label | 5,094 |
| Posts with 2 labels | 9,433 |
| Posts with 3 or more | 4,206 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 4,506 | 10,463 | 43.1% |
| 2 | Left, middle toxicity | 9,405 | 22,001 | 42.8% |
| 3 | Left, high toxicity | 4,899 | 13,096 | 37.4% |
| 4 | Right, low toxicity | 4,506 | 8,796 | 51.2% |
| 5 | Right, middle toxicity | 9,405 | 16,594 | 56.7% |
| 6 | Right, high toxicity | 4,899 | 6,630 | 73.9% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.5 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
