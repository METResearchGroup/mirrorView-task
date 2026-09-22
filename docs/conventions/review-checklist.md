# Review checklist for agents

Run this checklist before you publish or hand off rewritten issue text, PR descriptions, or other project prose. For detail on any row, see [prose-review.md](prose-review.md) and [github-issues-and-prs.md](github-issues-and-prs.md).

## Skills loaded

- [ ] Read [.cursor/skills/plain-writing/SKILL.md](/.cursor/skills/plain-writing/SKILL.md) for this edit.
- [ ] For a PR body, read [.cursor/skills/write-pr-description/SKILL.md](/.cursor/skills/write-pr-description/SKILL.md) and the matching `types/<type>/guide.md`.
- [ ] Optional Clarity pass: [clarity.addy.ie](https://clarity.addy.ie) criteria applied with least-invasive edits.

## Plain writing

- [ ] No em dashes, en dashes, or middle dots.
- [ ] No sentence with three or more clauses.
- [ ] No sentence-initial vague "This" / "That" / "These".
- [ ] No curly quotes.
- [ ] Headings use sentence case.
- [ ] Same word used for the same concept throughout.

## Self-contained (issues and PRs)

- [ ] No `Q<number>` labels; feature row schema spelled out or named once.
- [ ] No `Phase A` / `Phase B`; plain run names instead.
- [ ] No bare plan step numbers; issue or PR numbers or plain descriptions instead.
- [ ] No `epic`, `per the plan`, or `the user` (use repository owner when needed).
- [ ] No `later step` without an issue or PR number.
- [ ] Plan paths only on a trailing `Plan document:` line (if applicable).
- [ ] Opening paragraph states the main outcome before background.

## Facts (rewrites only)

- [ ] Side-by-side compare with the original: every number, command, path, gate, and observed result preserved.
- [ ] No new claims, commands, or numbers added.
- [ ] Approval gates not weakened.
- [ ] Cross-references (`Fixes`, `Stacked on`, out-of-scope issues) point at the correct numbers.

## Pull request structure

- [ ] Correct type outline (default / feature / bug / experiment).
- [ ] `Stacked on` line at the top when present.
- [ ] `Fixes` / `Part of` at the bottom.
- [ ] Commands, tables, Mermaid blocks, and Observed sections intact.
- [ ] Verification prose includes paths and constraints that appeared in the original (not only in code blocks).

## Parallel issues

- [ ] Sibling issues differ only in feature-specific fields (if part of a family).
- [ ] Shared phrases match ("the ten-post smoke run", "the full 200,000-post run", "the repository owner").

## Markdown hygiene

- [ ] Title line is `# <title>`; body starts after a blank line (for paste into GitHub).
- [ ] Fenced code blocks balanced.
- [ ] No Cursor agent footer or bot comment text in the body you publish.

## Grep gate

```bash
rg -n 'Q[0-9]+|Phase [AB]|—|–|\bStep [0-9]|\bepic\b|per the|the user|later step' <file>
```

- [ ] No matches outside `` `docs/plans/` `` or S3 path literals.
