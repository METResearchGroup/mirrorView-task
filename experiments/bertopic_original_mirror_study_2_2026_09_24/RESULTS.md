# Results

Date: 2026-09-24. This writeup answers five questions about topics in the original posts. Human review of the topic names is still pending.

Study 2 joins the June collection and the September collection. Topics were fit on the original wording of 19,763 posts, after duplicate wording was removed. The grouping found 100 topics and left 8,369 posts ungrouped (42.3%). Keep and remove votes were joined after the groups existed. They were not used to form the groups.

Keep rate is the share of votes to keep. For a topic, it is the average of that share across the posts in the topic. Across all 19,763 posts, the keep rate is 69.8%. Posts left ungrouped have the same keep rate, 69.8%.

Each post was labeled left leaning or right leaning, and low, medium, or high toxicity, when it was sampled. Raters are recorded as Democrats or Republicans. In the rater section, Democrat stands for left leaning raters and Republican stands for right leaning raters.

Topic names below are shortened from the words in each group. A person has not checked them.

## 1. What topics came out of the original posts?

The ten largest topics are climate, the border, MAGA and institutions, abortion, Trump and the media, and criticism of each party. Together they hold 6,268 of the 11,394 grouped posts.

| Topic | Posts | Keep rate |
| --- | ---: | ---: |
| Climate and fossil fuels | 1,122 | 81.8% |
| Border and immigration | 862 | 75.8% |
| MAGA and institutions | 851 | 59.1% |
| Abortion access | 690 | 75.2% |
| Trump media and lying | 636 | 59.3% |
| Criticism of Democrats | 598 | 69.3% |
| Criticism of Republicans | 566 | 59.0% |
| Biden and Trump blame | 358 | 67.6% |
| Billionaires and taxes | 326 | 76.6% |
| Abolish ICE | 259 | 62.1% |

The other 90 topics are smaller. Names and sizes for every topic are in `outputs/labels/original/20260924T135628Z/topic_labels.parquet`. Assignments are in `outputs/topics/original/20260924T135151Z/assignments.parquet`.

## 2. Do some topics get kept or removed more often?

Yes. Among the 23 topics with at least 100 posts, the keep rate runs from 31.7% to 81.8%.

| Topic | Posts | Keep rate |
| --- | ---: | ---: |
| Anti Trump harassment | 144 | 31.7% |
| Anti fascism messaging | 200 | 58.6% |
| Criticism of Republicans | 566 | 59.0% |
| MAGA and institutions | 851 | 59.1% |
| Trump media and lying | 636 | 59.3% |
| Abolish ICE | 259 | 62.1% |
| Trans rights in sports | 171 | 63.3% |
| Biden and Trump blame | 358 | 67.6% |
| Conservatism and religion | 229 | 69.2% |
| Criticism of Democrats | 598 | 69.3% |
| Open carry laws | 104 | 72.8% |
| Tariffs | 165 | 73.1% |
| US and Iran | 162 | 73.3% |
| Medicaid and SNAP | 212 | 73.4% |
| Democratic candidates | 251 | 73.5% |
| Supreme Court power | 124 | 74.1% |
| Abortion access | 690 | 75.2% |
| Border and immigration | 862 | 75.8% |
| Gun rights | 230 | 75.9% |
| Billionaires and taxes | 326 | 76.6% |
| Gun laws in schools | 155 | 79.3% |
| Sanctuary cities | 108 | 80.2% |
| Climate and fossil fuels | 1,122 | 81.8% |

A few smaller topics sit further out. Calling Trump a fascist is kept 45.0% of the time (19 posts). Accusations that Trump committed crimes are kept 46.9% of the time (56 posts). Gun violence awareness is kept 90.7% of the time (23 posts), climate and habitats 88.9% (27 posts), and the Florida property tax debate 87.7% (15 posts). These groups are small, so a few votes can move the percentage.

### Left leaning and right leaning posts

The stance of the post barely moves the overall keep rate.

| Stance of the post | Posts | Keep rate |
| --- | ---: | ---: |
| Left leaning | 11,386 | 69.0% |
| Right leaning | 8,377 | 70.9% |

Inside a topic, the gap is usually a few points. The rows below are the largest gaps among topics with at least 40 posts on each side.

| Topic | Left leaning | Right leaning | Gap |
| --- | --- | --- | --- |
| Tariffs | 69.1% (82 posts) | 77.0% (83 posts) | Right leaning posts are kept 7.9 points more |
| Conservatism and religion | 66.3% (143) | 73.9% (86) | Right leaning posts are kept 7.6 points more |
| Criticism of Republicans | 57.7% (468) | 65.2% (98) | Right leaning posts are kept 7.5 points more |
| Abolish ICE | 59.7% (171) | 66.9% (88) | Right leaning posts are kept 7.3 points more |
| Democratic candidates | 76.4% (124) | 70.8% (127) | Left leaning posts are kept 5.6 points more |
| Climate and fossil fuels | 82.9% (903) | 77.6% (219) | Left leaning posts are kept 5.3 points more |

### Low, medium, and high toxicity

Toxicity moves the keep rate much more than stance does. These rates use every post in the fit, including posts left ungrouped.

| Toxicity | Posts | Keep rate |
| --- | ---: | ---: |
| Low | 4,892 | 84.7% |
| Medium | 9,888 | 72.6% |
| High | 4,983 | 49.8% |

The same drop shows up inside topics. In every topic with at least 25 low toxicity posts and 25 high toxicity posts, the high toxicity posts are kept less. There are 15 such topics. The typical gap is about 32 points.

| Topic | Low | Medium | High |
| --- | --- | --- | --- |
| Criticism of Republicans | 79.2% (66) | 69.5% (272) | 40.5% (228) |
| Abortion access | 86.0% (240) | 73.1% (389) | 46.5% (61) |
| MAGA and institutions | 77.9% (98) | 65.6% (439) | 44.1% (314) |
| Border and immigration | 86.5% (243) | 76.7% (482) | 53.6% (137) |

## 3. Which topics are more common in left leaning posts, and which in right leaning posts?

Among the 11,394 grouped posts, 6,668 are left leaning and 4,726 are right leaning. The shares are the share of that side's grouped posts.

Left leaning posts show up more often in climate, in criticism of Trump's media behavior, and in criticism of Republicans. Right leaning posts show up more often in border and immigration, in criticism of Democrats, and in gun rights.

| Topic | Share of left leaning posts | Share of right leaning posts |
| --- | --- | --- |
| Climate and fossil fuels | 13.5% (903 posts) | 4.6% (219 posts) |
| Trump media and lying | 7.9% (528) | 2.3% (108) |
| Criticism of Republicans | 7.0% (468) | 2.1% (98) |
| Anti fascism messaging | 2.7% (179) | 0.4% (21) |
| Border and immigration | 3.1% (210) | 13.8% (652) |
| Criticism of Democrats | 3.8% (254) | 7.3% (344) |
| Gun rights | 0.6% (42) | 4.0% (188) |
| Biden and Trump blame | 1.9% (130) | 4.8% (228) |

## 4. Which topics are more common at low, medium, and high toxicity?

Of the grouped posts, 2,943 are low toxicity, 5,559 are medium, and 2,892 are high. Medium toxicity is the largest slice, and its topics look more like the overall mix. The clear shifts are at the two ends.

Low toxicity posts are more often about climate, abortion, and billionaires and taxes. High toxicity posts are more often attacks on Trump, MAGA and institutions, and criticism of Republicans. Anti Trump harassment is almost entirely in the high toxicity sample (140 of 144 posts).

| Topic | Low | Medium | High |
| --- | --- | --- | --- |
| Climate and fossil fuels | 20.5% (604) | 8.5% (471) | 1.6% (47) |
| Abortion access | 8.2% (240) | 7.0% (389) | 2.1% (61) |
| Billionaires and taxes | 4.8% (141) | 2.1% (117) | 2.4% (68) |
| Trump media and lying | 1.1% (33) | 3.6% (200) | 13.9% (403) |
| Anti Trump harassment | 0% (0) | 0.1% (4) | 4.8% (140) |
| MAGA and institutions | 3.3% (98) | 7.9% (439) | 10.9% (314) |
| Criticism of Republicans | 2.2% (66) | 4.9% (272) | 7.9% (228) |

## 5. Which topics did Democratic raters keep, and which did they remove? What about Republican raters?

These rates are the share of that group's votes. Democratic raters kept 69.4% of 52,864 votes. Republican raters kept 70.0% of 48,970 votes.

The topics each group was most likely to remove, and most likely to keep, are almost the same list. Both groups removed anti Trump harassment most often, at about 32%. Both groups kept climate and fossil fuels at about 82%. The lists below keep topics with at least 200 votes from that group.

| Topic | Democratic keep rate | Democratic votes |
| --- | ---: | ---: |
| Anti Trump harassment | 31.5% | 444 |
| MAGA and institutions | 57.6% | 2,308 |
| Criticism of Republicans | 59.1% | 1,500 |
| Trump media and lying | 59.4% | 1,788 |
| Anti fascism messaging | 59.7% | 571 |

| Topic | Democratic keep rate | Democratic votes |
| --- | ---: | ---: |
| Gun policy debate | 82.4% | 262 |
| Climate and fossil fuels | 82.2% | 2,872 |
| Gun laws in schools | 79.5% | 410 |
| Sanctuary cities | 78.6% | 266 |
| Gun rights | 77.6% | 602 |

| Topic | Republican keep rate | Republican votes |
| --- | ---: | ---: |
| Anti Trump harassment | 31.9% | 282 |
| Anti fascism messaging | 57.7% | 478 |
| Criticism of Republicans | 59.1% | 1,377 |
| Trump media and lying | 59.2% | 1,473 |
| MAGA and institutions | 60.8% | 2,059 |

| Topic | Republican keep rate | Republican votes |
| --- | ---: | ---: |
| Climate and fossil fuels | 81.5% | 2,893 |
| Sanctuary cities | 80.6% | 289 |
| Gun policy debate | 80.2% | 242 |
| Gun laws in schools | 79.1% | 369 |
| Mail and elections | 78.2% | 257 |

Where the two groups differ, the gap is small. Across 26 topics with at least 200 votes from each group, the typical gap is under 2 points. The largest gap is open carry laws: Democratic raters kept 75.8% of 289 votes, and Republican raters kept 68.3% of 249 votes. The next largest runs the other way. Republican raters kept Supreme Court posts at 77.6% (308 votes), and Democratic raters kept them at 71.5% (330 votes).

## Limits

Topics describe wording. They do not explain why a rater voted keep or remove. The topic names have not been checked by a person. Posts left ungrouped are in the overall keep rate and are not in the topic tables.

## Files

| Item | Path |
| --- | --- |
| Original topic assignments | `outputs/topics/original/20260924T135151Z` |
| Topic names | `outputs/labels/original/20260924T135628Z` |
| Keep rates by topic, stance, toxicity, and rater party | `outputs/analyses/outcomes/20260924T140052Z` |

`s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/`
