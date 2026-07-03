---
name: coding-guides
description: >-
  Project coding guides and Python run-from-root conventions.
environments:
  - local
---

# Coding guides

- Use uv and pyproject.toml for any Python code.
- Always run everything from root, and add the following to each Python file's docstring: "Run from root: PYTHONPATH=. uv run python ...".
