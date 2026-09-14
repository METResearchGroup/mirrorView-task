# Study progress, September 2026 run

Snapshot 2026_09_14-22:55:35 UTC. Export 2026_09_14-22:55:32.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,079 |
| Finished | 2,953 |
| Saved files | 2,973 |
| Labels | 59,460 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 76.1% |
| Label progress | 76.6% |
| Missing from export | 127 |
| Missing after 20-minute grace | 120 |
| Attrition after grace | 3.9% |

Prolific has finished 2,953 of 3,879 feeds (76.1%). Prolific has assigned a larger share of Democrat slots (95.4% assigned vs 63.4% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 38.9% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,850 | 1,780 | 1,940 | 95.4% | 96.2% |
| Republican | 1,229 | 1,173 | 1,939 | 63.4% | 95.4% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 24,746 | 11,034 | 35,780 | 69.2% | 30.8% | 69.2% | 30.8% | 165 | 11 |
| Republican | 16,784 | 6,896 | 23,680 | 70.9% | 29.1% | 70.9% | 29.1% | 156 | 8 |
| All | 41,530 | 17,930 | 59,460 | 69.8% | 30.1% | 69.9% | 30.1% | 321 | 19 |

Per-user keep rate (all finished): mean 69.9%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.1%, median 30.0%, SD 21.7%.

321 people kept every scored post. 19 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,678 | 14.8% |
| Democrat | Middle | 18,174 | 27.3% |
| Democrat | High | 9,928 | 49.8% |
| Republican | Low | 7,104 | 16.2% |
| Republican | Middle | 11,840 | 28.4% |
| Republican | High | 4,736 | 50.3% |

Pooled Democrat remove is 30.8% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,678 | 21.5% |
| Democrat | Middle | 18,174 | 50.8% |
| Democrat | High | 9,928 | 27.8% |
| Republican | Low | 7,104 | 30.0% |
| Republican | Middle | 11,840 | 50.0% |
| Republican | High | 4,736 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 20,190 | 31.8% |
| Democrat | Right | 15,590 | 29.6% |
| Republican | Left | 11,840 | 29.4% |
| Republican | Right | 11,840 | 28.8% |

## Attention

Pass rate 78.3% (2,311 passed, 642 failed).

Remove share among people who passed: 28.7%. Among people who failed: 35.2%.

276 of 321 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.7%. Democrat passers 29.5%. Republican passers 27.5%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,862 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,348 |
| Posts with 2 labels | 4,196 |
| Posts with 3 or more | 13,318 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 7,591 | 10,463 | 72.5% |
| 2 | Left, middle toxicity | 16,015 | 22,001 | 72.8% |
| 3 | Left, high toxicity | 8,424 | 13,096 | 64.3% |
| 4 | Right, low toxicity | 7,191 | 8,796 | 81.8% |
| 5 | Right, middle toxicity | 13,999 | 16,594 | 84.4% |
| 6 | Right, high toxicity | 6,240 | 6,630 | 94.1% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.8 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
