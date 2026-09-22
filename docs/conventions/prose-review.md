# Prose review criteria

Use this document when you review or rewrite reader-facing text in this repository. It does not replace the linked skills. It tells you which skill to apply and adds repository-specific discipline on top.

## Layer 1: Plain writing (required)

Read and follow [.cursor/skills/plain-writing/SKILL.md](/.cursor/skills/plain-writing/SKILL.md) in full before you edit prose for this project.

High-signal rules agents miss most often:

- Use simple words. Avoid AI filler ("leverage", "robust", "delve", "landscape").
- Write complete sentences. No fragments in prose.
- Do not use em dashes, en dashes, or middle dots. Use a period, a comma, "and", or "to".
- Do not use a colon to join two clauses. Use a colon only to introduce a list.
- Do not start a sentence with "This", "That", or "These" when they point at a whole prior idea. Name the thing.
- Do not write a sentence with three or more clauses. Split it.
- Prefer one repeated word over a synonym swap for the same concept.
- Straight quotes only. Sentence case in headings. No bold as decoration.

For long explanations aimed at a reader with no project context, the user may ask for `/plain-writing deslopify`. That format starts with the main conclusion, then background, mechanism, evidence, and risks.

## Layer 2: Clarity (recommended second pass)

After plain writing, apply the ideas in [Clarity](https://clarity.addy.ie) by Addy Osmani. You can install the Clarity agent skill with `npx skills add addyosmani/clarity` and use `/clarity rewrite` or `/clarity review` on a named file.

Use Clarity for documentation, issues, and PR descriptions as **guide** or **reference** prose, not as essays. Skip thesis hooks, authorial position-taking, and closing summaries.

Criteria that matter most here:

| Criterion | What to do |
| --------- | ---------- |
| Know what the reader brings and what they need | State the outcome before background. Do not assume the reader sat in the planning conversation. |
| Decide what they take away | The first paragraph should say what the item does or changes. |
| Make every sentence pay | Remove a sentence that repeats another in different words. |
| Be specific enough to be wrong | Keep numbers, paths, commands, and column names. Do not blur a fact into a vague phrase. |
| Put someone in the sentence | Name the component, script, or person when an inanimate subject is doing an action. |
| Say the relation instead of implying it | Add "because", "so", "although", or "when" where two sentences only sit next to each other. |
| Stop where the thought stops | No recap paragraph at the end. |

Clarity safeguard: do not invent facts, quotes, or experience to sound clearer. If a sentence needs a detail the source does not have, ask the author or cut the sentence.

## Layer 3: Fact discipline (required for rewrites)

When you rewrite existing text, treat fact discipline as strict.

- Every number, command, path, dataset id, observed result, gate, and constraint in the original must appear in the rewrite with the same force.
- Do not add claims, commands, examples, or numbers that are not in the source unless the user explicitly asks for new content.
- Do not drop verification evidence (model names, S3 prefixes, pytest counts, smoke output) to shorten a PR body.
- Do not "improve" a gate by weakening it (for example changing "reviewed and approved" to "reviewed" only).
- Do not invent who performs an action (for example "the repository owner must post estimates" when the original only says estimates "are posted").

If you replace planning shorthand with issue or PR numbers, use the correct GitHub link target (#181, PR #197, and so on). Wrong cross-references are fact errors.

## Layer 4: Medium-specific shape

| Medium | Optimize for | Keep |
| ------ | ------------ | ---- |
| GitHub issue | What to do, done when, gates | Done when lists, ship-one-PR lines, approval gates |
| Pull request | Behavior change, verification | Commands, expected output, observed results, Mermaid diagrams, `Fixes` / `Part of` lines |
| Runbook | Correct completion | Headings, warnings, exact commands |
| Plan document | Spec for implementers | May use step numbers inside `docs/plans/`; linked issues and PRs should still read standalone |

Pull request bodies: classify with the [write PR description skill](/.cursor/skills/write-pr-description/SKILL.md) and use that type's outline. Do not invent a hybrid section list.

## Review output format

When you review prose for another agent or the user, report findings in this shape:

```text
Passage:   shortest quote that locates the issue
Verdict:   keep | revise | ask-author | cut
Rule:      plain-writing #N | Clarity: <criterion> | self-contained | fact | structure
Why:       what the passage does wrong
Fix:       exact replacement sentence, or what to ask the author
```

Group findings by severity: fact errors first, then non-self-contained references, then style.
