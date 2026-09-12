# Conventions for agents

This folder holds review criteria and best practices for prose written in this repository. Agents should use these documents when they draft, rewrite, or review GitHub issues, pull request descriptions, runbooks, plans, and other reader-facing text.

## External references (read first for prose)

| Resource | When to use it |
| -------- | -------------- |
| [Plain writing skill](/.cursor/skills/plain-writing/SKILL.md) | Default style for all prose written for this project. Sentence rules, word choice, punctuation, and patterns to avoid. Run `/plain-writing` or `/plain-writing deslopify` when the user asks for that style. |
| [Clarity](https://clarity.addy.ie) (Addy Osmani) | Second pass after plain writing. Useful, clear, honest prose for a specific reader. Install with `npx skills add addyosmani/clarity` if you use Clarity modes (`/clarity rewrite`, `/clarity review`). |
| [Write PR description skill](/.cursor/skills/write-pr-description/SKILL.md) | Structure for pull request bodies by type (experiment, feature, bug, default). Read the matching `types/<type>/guide.md` before drafting a PR description. |
| [Vocabulary conventions](https://github.com/mark-torres10/ai_tools/blob/main/conventions/vocabulary.md) | Naming and domain terms (referenced from `AGENTS.md`). |

## Documents in this folder

| Document | Purpose |
| -------- | ------- |
| [prose-review.md](prose-review.md) | How to review any prose: layered criteria (plain writing, Clarity, fact discipline). |
| [github-issues-and-prs.md](github-issues-and-prs.md) | Rules specific to issue and PR text: self-contained wording, structure, parallel issue families. |
| [review-checklist.md](review-checklist.md) | Short checklist agents can run before posting or after rewriting. |

## Recommended workflow

1. Draft or rewrite the text using the [plain writing skill](/.cursor/skills/plain-writing/SKILL.md).
2. For pull requests, shape the body with the [write PR description skill](/.cursor/skills/write-pr-description/SKILL.md).
3. Apply [prose-review.md](prose-review.md) and, for GitHub items, [github-issues-and-prs.md](github-issues-and-prs.md).
4. Optional second pass using [Clarity](https://clarity.addy.ie) criteria (see prose-review.md). Make the least invasive edit that fixes a real problem.
5. Run [review-checklist.md](review-checklist.md) and fix any failing item before you publish.

## Where these rules came from

The GitHub-specific rules were distilled from a full rewrite of [issue #180](https://github.com/METResearchGroup/mirrorView-task/issues/180) and its sub-issues and implementation PRs (September 2026). That pass scrubbed planning shorthand, applied plain writing and PR-description outlines, and ran a separate Clarity review. The failures that QA caught (dropped facts, invented sentences, vague "later step" pointers) are encoded here so future agents do not repeat them.
