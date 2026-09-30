"""Fill the Study 2 feature page template."""

from __future__ import annotations

import json


def build_page_data(by_lean, by_toxicity, by_remove_votes, details: dict) -> dict:
    """Assemble the JSON the page script reads.

    Parameters
    ----------
    by_lean, by_toxicity, by_remove_votes
        Top-feature tables.
    details
        Feature key to name and description.

    Returns
    -------
    dict
        Tables plus the full feature list, sorted by name.
    """
    features = [
        {"key": key, "name": value["name"], "description": value["description"]}
        for key, value in sorted(details.items(), key=lambda item: item[1]["name"])
    ]
    return {
        "lean": by_lean.to_dict(orient="records"),
        "toxicity": by_toxicity.to_dict(orient="records"),
        "remove_votes": by_remove_votes.to_dict(orient="records"),
        "features": features,
    }


def render_page(
    template: str,
    styles: str,
    script: str,
    charts: dict[str, str],
    data: dict,
) -> str:
    """Replace the page placeholders with styles, script, charts, and data.

    Parameters
    ----------
    template
        HTML with ``{{STYLES}}``, ``{{SCRIPT}}``, ``{{CHARTS}}``, and ``{{DATA_JSON}}``.
    styles
        CSS text.
    script
        JavaScript text.
    charts
        Chart name to SVG markup. Requires ``lean`` and ``toxicity``.
    data
        Object encoded into the page.

    Returns
    -------
    str
        Self-contained HTML.

    Raises
    ------
    ValueError
        When a chart is missing or a placeholder remains.
    """
    for name in ("lean", "toxicity"):
        if name not in charts or not charts[name].strip():
            raise ValueError(f"missing chart: {name}")
    charts_html = (
        f'<div class="chart" id="lean-chart">{charts["lean"]}</div>'
        f'<div class="chart" id="toxicity-chart">{charts["toxicity"]}</div>'
    )
    page = (
        template.replace("{{STYLES}}", styles)
        .replace("{{SCRIPT}}", script)
        .replace("{{CHARTS}}", charts_html)
        .replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False))
    )
    if "{{" in page:
        raise ValueError("a placeholder was left in the page")
    return page
