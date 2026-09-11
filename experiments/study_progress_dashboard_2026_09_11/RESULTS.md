# Study progress, September 2026 run

Snapshot 2026_09_11-02:50:36 UTC. Export 2026_09_11-02:49:19.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 1,085 |
| Finished | 1,031 |
| Saved files | 1,033 |
| Labels | 20,660 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 26.6% |
| Label progress | 26.6% |
| Missing from export | 54 |
| Missing after 20-minute grace | 51 |
| Attrition after grace | 4.7% |

Prolific has finished 1,031 of 3,879 feeds (26.6%). Prolific has assigned a larger share of Democrat slots (32.9% assigned vs 23.0% Republican). The busiest assignment hour is 2026-09-10 18:00 UTC, and assignments in the three busiest hours are 82.8% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 639 | 611 | 1,940 | 32.9% | 95.6% |
| Republican | 446 | 420 | 1,939 | 23.0% | 94.2% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 8,330 | 3,890 | 12,220 | 68.2% | 31.8% | 68.2% | 31.8% | 51 | 3 |
| Republican | 5,987 | 2,453 | 8,440 | 70.9% | 29.1% | 71.0% | 29.0% | 55 | 4 |
| All | 14,317 | 6,343 | 20,660 | 69.3% | 30.7% | 69.3% | 30.7% | 106 | 7 |

Per-user keep rate (all finished): mean 69.3%, median 70.0%, SD 21.8%.

Per-user remove rate (all finished): mean 30.7%, median 30.0%, SD 21.8%.

106 people kept every scored post. 7 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 2,444 | 14.6% |
| Democrat | Middle | 6,110 | 27.9% |
| Democrat | High | 3,666 | 49.9% |
| Republican | Low | 2,532 | 17.1% |
| Republican | Middle | 4,220 | 27.8% |
| Republican | High | 1,688 | 50.1% |

Pooled Democrat remove is 31.8% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 2,444 | 20.0% |
| Democrat | Middle | 6,110 | 50.0% |
| Democrat | High | 3,666 | 30.0% |
| Republican | Low | 2,532 | 30.0% |
| Republican | Middle | 4,220 | 50.0% |
| Republican | High | 1,688 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 6,110 | 32.3% |
| Democrat | Right | 6,110 | 31.4% |
| Republican | Left | 4,220 | 29.2% |
| Republican | Right | 4,220 | 28.9% |

## Attention

Pass rate 78.7% (811 passed, 220 failed).

Remove share among people who passed: 29.5%. Among people who failed: 35.2%.

90 of 106 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.5%. Democrat passers 30.6%. Republican passers 27.7%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 17,215 |
| Catalog posts | 18,899 |
| Posts with 1 label | 13,954 |
| Posts with 2 labels | 3,077 |
| Posts with 3 or more | 184 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 2,488 | 10,463 | 23.8% |
| 2 | Left, middle toxicity | 5,165 | 22,001 | 23.5% |
| 3 | Left, high toxicity | 2,677 | 13,096 | 20.4% |
| 4 | Right, low toxicity | 2,488 | 8,796 | 28.3% |
| 5 | Right, middle toxicity | 5,165 | 16,594 | 31.1% |
| 6 | Right, high toxicity | 2,677 | 6,630 | 40.4% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.6 minutes.

## Outputs

* `index.html`
* `outputs/dashboard_payload.json`
