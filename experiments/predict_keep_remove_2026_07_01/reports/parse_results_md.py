"""Parse LaTeX metric tables embedded in results.md."""

from __future__ import annotations

import re
from typing import Any


def parse_latex_array_rows(array_block: str) -> list[dict[str, Any]]:
    """Parse rows like::

        \\text{Logistic regression} & \\text{Test} & 0.695 & ... \\\\
    """
    row_re = re.compile(
        r"\\text\{(?P<model>[^}]*)\}\s*&\s*\\text\{(?P<split>[^}]*)\}\s*&\s*"
        r"(?P<accuracy>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<precision>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<recall>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<f1>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<roc_auc>-?\d+(?:\.\d+)?)",
        flags=re.MULTILINE,
    )

    out: list[dict[str, Any]] = []
    for m in row_re.finditer(array_block):
        d = m.groupdict()
        out.append(
            {
                "model": str(d["model"]).strip(),
                "split": str(d["split"]).strip(),
                "accuracy": float(d["accuracy"]),
                "precision": float(d["precision"]),
                "recall": float(d["recall"]),
                "f1": float(d["f1"]),
                "roc_auc": float(d["roc_auc"]),
            }
        )
    return out


def extract_latex_array_blocks(md_text: str) -> list[str]:
    """Return all ``\\begin{array}...\\end{array}`` blocks in document order."""
    array_re = re.compile(r"\\begin\{array\}.*?\\end\{array\}", flags=re.DOTALL)
    return array_re.findall(md_text)


def extract_first_n_array_blocks(md_text: str, n: int) -> list[str]:
    blocks = extract_latex_array_blocks(md_text)
    if len(blocks) < n:
        raise ValueError(f"Expected at least {n} LaTeX array blocks, found {len(blocks)}")
    return blocks[:n]


def extract_ablation_array_block(md_text: str) -> str:
    parts = md_text.split("### Ablation results", 1)
    if len(parts) != 2:
        raise ValueError("Could not find '### Ablation results' heading.")

    after_heading = parts[1]
    m = re.search(r"\\begin\{array\}.*?\\end\{array\}", after_heading, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find LaTeX array block under '### Ablation results'.")
    return m.group(0)
