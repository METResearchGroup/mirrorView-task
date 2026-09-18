# Study progress, September 2026 run

Snapshot 2026_09_18-15:05:48 UTC. Export 2026_09_18-15:05:45.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,884 |
| Finished | 3,746 |
| Saved files | 3,833 |
| Labels | 76,660 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 96.6% |
| Label progress | 98.8% |
| Missing from export | 139 |
| Missing after 20-minute grace | 136 |
| Attrition after grace | 3.5% |

Prolific has finished 3,746 of 3,879 feeds (96.6%). Prolific has assigned a larger share of Democrat slots (105.8% assigned vs 94.4% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 30.9% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 2,053 | 1,980 | 1,940 | 105.8% | 96.4% |
| Republican | 1,831 | 1,766 | 1,939 | 94.4% | 96.5% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 27,544 | 12,476 | 40,020 | 68.8% | 31.2% | 68.8% | 31.2% | 173 | 13 |
| Republican | 25,920 | 10,720 | 36,640 | 70.7% | 29.3% | 70.8% | 29.2% | 232 | 10 |
| All | 53,464 | 23,196 | 76,660 | 69.7% | 30.3% | 69.8% | 30.2% | 405 | 23 |

Per-user keep rate (all finished): mean 69.8%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.2%, median 30.0%, SD 21.7%.

405 people kept every scored post. 23 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 8,350 | 14.9% |
| Democrat | Middle | 19,897 | 27.3% |
| Democrat | High | 11,773 | 49.3% |
| Republican | Low | 11,253 | 16.7% |
| Republican | Middle | 18,625 | 28.9% |
| Republican | High | 6,762 | 51.1% |

Pooled Democrat remove is 31.2% vs Republican 29.3%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 8,350 | 20.9% |
| Democrat | Middle | 19,897 | 49.7% |
| Democrat | High | 11,773 | 29.4% |
| Republican | Low | 11,253 | 30.7% |
| Republican | Middle | 18,625 | 50.8% |
| Republican | High | 6,762 | 18.5% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 23,260 | 32.1% |
| Democrat | Right | 16,760 | 29.8% |
| Republican | Left | 20,620 | 30.0% |
| Republican | Right | 16,020 | 28.3% |

## Attention

Pass rate 77.4% (2,901 passed, 845 failed).

Remove share among people who passed: 28.8%. Among people who failed: 35.0%.

343 of 405 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.8%. Democrat passers 30.0%. Republican passers 27.4%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,866 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,148 |
| Posts with 2 labels | 1,810 |
| Posts with 3 or more | 15,908 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 10,553 | 10,463 | 100.9% |
| 2 | Left, middle toxicity | 21,533 | 22,001 | 97.9% |
| 3 | Left, high toxicity | 11,794 | 13,096 | 90.1% |
| 4 | Right, low toxicity | 9,050 | 8,796 | 102.9% |
| 5 | Right, middle toxicity | 16,989 | 16,594 | 102.4% |
| 6 | Right, high toxicity | 6,741 | 6,630 | 101.7% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.9 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
