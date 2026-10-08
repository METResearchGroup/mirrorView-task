# DSPy GEPA optimization for Study 2

## Split audit

The prepared input has 4,051 unanimous source rows, 10 excluded prompt examples, 4,041 eligible rows, and a 405-row pilot cohort.
Optimization has 222 rows, and GEPA validation, development, and test each have 61 rows.
Remove counts are 17, 5, 5, and 5.

## Run provenance

- Pilot run: `study2-dspy-gepa-2026-10-01-pilot`
- Approved smoke run: `study2-dspy-gepa-2026-10-01-smoke-b`
- Analysis artifacts: `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_optimization_2026_09_30/runs/study2-dspy-gepa-2026-10-01-pilot/`
- Weave project: `mind_technology_lab/dspy_gepa_optimization_2026_09_30`
- Model: `us.openai.gpt-5.6-terra`
- Packages: DSPy 3.4.0, GEPA 0.1.4, Weave 0.53.11

## Selection rule

The selected prompt has the highest balanced validation accuracy.
An exact tie uses the shorter instruction, then the earlier candidate index.
Development F1 did not change the selection. Threshold is 0.5, and remove is the positive class.

## Development metrics

| Program | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Selected program | 61 | 0.727273 | 0.950820 | 0.800000 | 0.666667 |

## Human label note

Development and test each contain five remove rows. Each missed remove changes recall by 20 percentage points.

## Prompt comparison

### Original instruction

```text
We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.


The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.


Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

Allow Or Remove?
```

### Optimized instruction

```text
We are developing a social-media platform for political discussion. Review a pair of political mirror posts: the second expresses an opposing political perspective. Apply the same standard to both posts regardless of ideology, candidate, party, or viewpoint.

Return **Remove** if either post contains, endorses, or celebrates content that meaningfully harms a healthy political-discussion environment, including:
- Credible threats, calls for violence, glorification of violence, or exhortations to physically fight political opponents.
- Apocalyptic or life-threatening political claims combined with mobilizing language, such as saying an election will kill or destroy people and urging others to fight, defend the country, or act.
- Harassment, intimidation, targeted abusive attacks, or profanity-laced vilification directed at a person or political group.
- Dehumanizing or demonizing labels for people or groups, including portraying them as monstrous, inhuman, or evil beings.
- Hateful attacks or encouragement of illegal or dangerous conduct.

Allow ordinary political opinions, policy criticism, electoral claims, partisan rhetoric, and nonviolent advocacy. Strong disagreement alone is not enough for removal. However, do not treat profanity or dehumanizing attacks as acceptable merely because they occur in political debate.

Decide from the posts’ content and context, not whether you agree with their politics. If either post warrants removal, select **Remove**; otherwise select **Allow**.

Allow Or Remove?
```

## Model metrics

### Test posts

| Program | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 61 | 0.285714 | 0.918033 | 0.200000 | 0.500000 |
| Selected | 61 | 0.545455 | 0.918033 | 0.600000 | 0.500000 |

## Limitations

This is a 405-row pilot. The metrics are directional because each test split has five remove rows.
