# GitHub issues and pull requests

Rules for issue descriptions and pull request bodies in this repository. Use together with [prose-review.md](prose-review.md) and the [plain writing](/.cursor/skills/plain-writing/SKILL.md) and [write PR description](/.cursor/skills/write-pr-description/SKILL.md) skills.

## Self-contained text

A reader who has GitHub access but did not read `docs/plans/` or attend the planning thread must understand the issue or PR from the body alone.

### Remove or replace planning shorthand

Do not leave these in issue or PR bodies:

| Pattern | Replace with |
| ------- | ------------ |
| `Q44`, `Q12`, "question 44" | The **feature row schema**: `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, and the feature's label column. After the first full list, you may write "the feature row schema". |
| `Phase A`, `Phase B` | What the phase is: "the ten-post smoke run", "the full 200,000-post run". |
| `Step 1`, `Step 4 of the epic`, `Steps 8 through 14` | The owning **issue** or **pull request** number, or a plain description ("the seven prerequisite implementation issues #181 to #187"). |
| `epic`, `per the epic`, `per the plan`, `child plan`, `step spec` | Plain meaning, or delete if it adds nothing. |
| `the user`, `user sign-off` | `the repository owner` on first mention, then `the owner`, when the text means the person who must approve production work. |
| `later step`, `a later PR` | The issue or PR number (#185, #186) or "out of scope for this PR". |
| `the approved ten-post smoke flow` | `the ten-post smoke run` |

Plan file paths may stay in the repository, but the body must not depend on them. Move inline `Plan step: docs/plans/...` lines to a single trailing line:

```markdown
Plan document: `docs/plans/<campaign>/steps/stepN.md`, `docs/plans/<child-plan>/`
```

Put that line after the main content and before `Fixes #n` / `Part of #n` on pull requests. Parent tracking issues that never had a plan path do not need a fabricated one.

### Keep GitHub-native links

These are self-contained because GitHub resolves them:

- `Fixes #181`, `Part of #180`
- `Stacked on #200, #199, and #198. Merge those first.`
- Issue lists in tracking PRs
- Markdown links to issues and pull requests

## Issue description shape

Typical structure:

1. Opening paragraph: what the issue produces or runs (lead with the outcome).
2. Constraints (artifacts only, no product code changes, and so on) when true.
3. `Done when:` bullet list with testable conditions.
4. Approval or sign-off paragraph when production work is gated.
5. `Ship as one PR. Do not bundle with sibling issues.` when the workflow requires it.
6. `Plan document:` line when a plan exists (see above).

### Parallel issue families

When several issues are near copies (for example one feature per issue), keep identical structure and wording except for feature-specific facts (feature name, label column, accepted values, plan path). Run `diff` between siblings before you publish. Do not add a sentence to one sibling because it "should" match others unless every original had that sentence.

### Opening verbs for smoke plus production runs

Avoid `Run the ten-post smoke run and full 200,000-post ...` (repeated "run"). Prefer:

```markdown
Complete the ten-post smoke run and the full 200,000-post OpenAI Batch generation for `<feature>` only.
```

## Pull request description shape

Classify the PR with the [write PR description skill](/.cursor/skills/write-pr-description/SKILL.md):

| Type | Sections |
| ---- | -------- |
| Default (chore, infra, docs, migration) | Problem, Solution, Purpose, How to run |
| Feature | Summary, Purpose, Architecture, Interfaces, How to run, Limitations or Risks when needed |
| Bug | Summary, Purpose, Reproduction, Root cause, Fix, How to verify |
| Experiment | Per `types/experiments/guide.md` |

Shared rules:

- Describe behavior and outcomes, not a file changelog.
- Keep every command, expected result, and observed bullet from verification. Shorten only by removing repetition, not evidence.
- Leave Mermaid diagram blocks unchanged unless the flow actually changed.
- Put `Stacked on ...` immediately after the title block (before `## Summary` or `## Problem`).
- End with `Plan document:` (if any), then `Fixes #n`, then `Part of #n`.

Component lists may use `` `Name`: description `` instead of em-dash separators.

Replace vague openings:

| Avoid | Prefer |
| ----- | ------ |
| This PR adds... | The pull request adds... |
| This change writes... | The pull request writes... |

## Common QA failures (from issue #180 rewrite)

Encode these as hard checks:

1. **Dropped approval wording.** If the original gate says prerequisite PRs are "reviewed and approved", keep both words.
2. **Invented actor.** Do not name who posts smoke estimates unless the original does.
3. **Dropped verification facts.** Keep model names, post counts, "nothing written to S3", and full S3 prefix URLs in verification prose, not only in an Observed code block.
4. **Invented scope sentence.** Do not add "documentation and run artifacts only" to an issue whose original lacked it.
5. **Wrong stack order.** `Stacked on` belongs at the top of the PR body, not at the bottom.
6. **Parallelism drift.** Seven feature issues must differ only in feature-specific fields.
7. **Synonym scrub that loses meaning.** Replacing "Steps 3 and 2" with "later work" without naming #182 and #183 is a failure.

## Automated grep before publish

Run a pattern scan on the final markdown (allow hits only inside `` `docs/plans/...` `` paths or literal S3 object paths):

```bash
rg -n 'Q[0-9]+|Phase [AB]|—|–|\bStep [0-9]|\bepic\b|per the|child plan|step spec|\bthe user\b|later step|this step' <file>
```

Zero hits outside allowed paths is the target.
