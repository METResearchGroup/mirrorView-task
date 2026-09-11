# Study progress, September 2026 run

Snapshot 2026_09_11-16:09:57 UTC. Export 2026_09_11-16:09:56.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 1,151 |
| Finished | 1,094 |
| Saved files | 1,096 |
| Labels | 21,920 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 28.2% |
| Label progress | 28.2% |
| Missing from export | 57 |
| Missing after 20-minute grace | 54 |
| Attrition after grace | 4.7% |

Prolific has finished 1,094 of 3,879 feeds (28.2%). Prolific has assigned a larger share of Democrat slots (34.7% assigned vs 24.7% Republican). The busiest assignment hour is 2026-09-10 18:00 UTC, and assignments in the three busiest hours are 78.0% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 673 | 641 | 1,940 | 34.7% | 95.2% |
| Republican | 478 | 453 | 1,939 | 24.7% | 94.8% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 8,755 | 4,065 | 12,820 | 68.3% | 31.7% | 68.3% | 31.7% | 55 | 3 |
| Republican | 6,440 | 2,660 | 9,100 | 70.8% | 29.2% | 70.8% | 29.2% | 58 | 4 |
| All | 15,195 | 6,725 | 21,920 | 69.3% | 30.7% | 69.3% | 30.7% | 113 | 7 |

Per-user keep rate (all finished): mean 69.3%, median 70.0%, SD 21.9%.

Per-user remove rate (all finished): mean 30.7%, median 30.0%, SD 21.9%.

113 people kept every scored post. 7 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 2,564 | 14.6% |
| Democrat | Middle | 6,410 | 27.8% |
| Democrat | High | 3,846 | 49.7% |
| Republican | Low | 2,730 | 17.1% |
| Republican | Middle | 4,550 | 28.0% |
| Republican | High | 1,820 | 50.5% |

Pooled Democrat remove is 31.7% vs Republican 29.2%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 2,564 | 20.0% |
| Democrat | Middle | 6,410 | 50.0% |
| Democrat | High | 3,846 | 30.0% |
| Republican | Low | 2,730 | 30.0% |
| Republican | Middle | 4,550 | 50.0% |
| Republican | High | 1,820 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 6,410 | 32.2% |
| Democrat | Right | 6,410 | 31.2% |
| Republican | Left | 4,550 | 29.4% |
| Republican | Right | 4,550 | 29.1% |

## Attention

Pass rate 78.7% (861 passed, 233 failed).

Remove share among people who passed: 29.4%. Among people who failed: 35.4%.

97 of 113 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.4%. Democrat passers 30.3%. Republican passers 28.0%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 17,578 |
| Catalog posts | 18,899 |
| Posts with 1 label | 13,507 |
| Posts with 2 labels | 3,801 |
| Posts with 3 or more | 270 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 2,647 | 10,463 | 25.3% |
| 2 | Left, middle toxicity | 5,480 | 22,001 | 24.9% |
| 3 | Left, high toxicity | 2,833 | 13,096 | 21.6% |
| 4 | Right, low toxicity | 2,647 | 8,796 | 30.1% |
| 5 | Right, middle toxicity | 5,480 | 16,594 | 33.0% |
| 6 | Right, high toxicity | 2,833 | 6,630 | 42.7% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
