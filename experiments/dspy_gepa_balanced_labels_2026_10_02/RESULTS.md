# Balanced keep and remove GEPA ablation

This ablation uses a new 405-post cohort with 203 keep posts and 202 remove posts.
The finished natural-prevalence run is unchanged.

## Cohort

| Split | Posts | Keep | Remove |
| --- | ---: | ---: | ---: |
| Optimization | 222 | 111 | 111 |
| GEPA validation | 61 | 31 | 30 |
| Development | 61 | 30 | 31 |
| Test | 61 | 31 | 30 |

## Run

- Run ID: `study2-gepa-balanced-2026-10-02-pilot`
- Artifacts: `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_balanced_labels_2026_10_02/runs/study2-gepa-balanced-2026-10-02-pilot/`
- Model: `us.openai.gpt-5.6-terra`
- Selected candidate: 4
- Balanced validation accuracy: 1.0
- Comparison run: `study2-dspy-gepa-2026-10-01-pilot`

## Development

| Program | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 61 | 0.565217 | 0.672131 | 0.419355 | 0.866667 |
| Selected | 61 | 0.816901 | 0.786885 | 0.935484 | 0.725000 |

## Test

| Program | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 61 | 0.680851 | 0.754098 | 0.533333 | 0.941176 |
| Selected | 61 | 0.835821 | 0.819672 | 0.933333 | 0.756757 |

## Optimized instruction

```text
You are reviewing a pair of political mirror posts for a political social media platform. The posts express analogous messages from opposing viewpoints and are not replies. Apply the same standards regardless of ideology, party, candidate, movement, or protected characteristic.

Decide whether the pair supports healthy political discussion.

Allow substantive political speech, including criticism of politicians, parties, policies, institutions, and movements; claims that policies cause harm; and forceful, blunt, or emotional disagreement.

Remove if either post contains:
- Targeted hostile abuse, harassment, threats, calls for harm, dehumanization, or degrading/contemptuous language.
- Sweeping attacks on political groups or their members.
- Obscene, aggressively dismissive, taunting, mocking, or inflammatory language directed at opponents or their views.
- Unsupported assertions or insinuations that a named person committed serious criminal, sexual, or similarly grave misconduct. A bare accusation is not protected political criticism merely because it concerns a public figure.

Distinguish criticism from abuse:
- Allow criticism focused on actions, policies, consequences, public statements, or documented conduct, when not abusively framed.
- Remove language whose main effect is to insult, humiliate, provoke hostility toward, or contemptuously dismiss a political person, group, or viewpoint.
- Do not remove solely for strong political disagreement. Remove only when abusive, threatening, degrading, inflammatory, or gravely accusatory as described above.

Make one binary decision for the pair:
- Allow only if both posts should remain.
- Remove if either post should be removed.

Return only the decision.

Allow Or Remove?
```

One missed remove changes development recall by about 3.2 percentage points and test recall by about 3.3 percentage points.
