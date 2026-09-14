# Study progress, September 2026 run

Snapshot 2026_09_14-22:52:54 UTC. Export 2026_09_14-22:52:51.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,077 |
| Finished | 2,952 |
| Saved files | 2,972 |
| Labels | 59,440 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 76.1% |
| Label progress | 76.6% |
| Missing from export | 126 |
| Missing after 20-minute grace | 119 |
| Attrition after grace | 3.9% |

Prolific has finished 2,952 of 3,879 feeds (76.1%). Prolific has assigned a larger share of Democrat slots (95.3% assigned vs 63.3% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 39.0% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,849 | 1,780 | 1,940 | 95.3% | 96.3% |
| Republican | 1,228 | 1,172 | 1,939 | 63.3% | 95.4% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 24,746 | 11,034 | 35,780 | 69.2% | 30.8% | 69.2% | 30.8% | 165 | 11 |
| Republican | 16,769 | 6,891 | 23,660 | 70.9% | 29.1% | 70.9% | 29.1% | 156 | 8 |
| All | 41,515 | 17,925 | 59,440 | 69.8% | 30.2% | 69.9% | 30.1% | 321 | 19 |

Per-user keep rate (all finished): mean 69.9%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.1%, median 30.0%, SD 21.7%.

321 people kept every scored post. 19 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,678 | 14.8% |
| Democrat | Middle | 18,174 | 27.3% |
| Democrat | High | 9,928 | 49.8% |
| Republican | Low | 7,098 | 16.2% |
| Republican | Middle | 11,830 | 28.4% |
| Republican | High | 4,732 | 50.2% |

Pooled Democrat remove is 30.8% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,678 | 21.5% |
| Democrat | Middle | 18,174 | 50.8% |
| Democrat | High | 9,928 | 27.8% |
| Republican | Low | 7,098 | 30.0% |
| Republican | Middle | 11,830 | 50.0% |
| Republican | High | 4,732 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 20,190 | 31.8% |
| Democrat | Right | 15,590 | 29.6% |
| Republican | Left | 11,830 | 29.4% |
| Republican | Right | 11,830 | 28.8% |

## Attention

Pass rate 78.2% (2,310 passed, 642 failed).

Remove share among people who passed: 28.7%. Among people who failed: 35.2%.

276 of 321 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.7%. Democrat passers 29.5%. Republican passers 27.5%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,862 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,350 |
| Posts with 2 labels | 4,197 |
| Posts with 3 or more | 13,315 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 7,588 | 10,463 | 72.5% |
| 2 | Left, middle toxicity | 16,010 | 22,001 | 72.8% |
| 3 | Left, high toxicity | 8,422 | 13,096 | 64.3% |
| 4 | Right, low toxicity | 7,188 | 8,796 | 81.7% |
| 5 | Right, middle toxicity | 13,994 | 16,594 | 84.3% |
| 6 | Right, high toxicity | 6,238 | 6,630 | 94.1% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.8 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
