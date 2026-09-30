"""Load the evident-charts helper from the local clone."""

from __future__ import annotations

import sys

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    EVIDENT_CHARTS_SCRIPTS_DIR,
)


def short_label(name: str, limit: int) -> str:
    """Shorten a feature name so a panel can show the bar and the count.

    Parameters
    ----------
    name
        Full feature name. The tables on the page keep the full name.
    limit
        Maximum characters, including an ellipsis when the name is cut.

    Returns
    -------
    str
        ``name`` when it already fits, otherwise a shortened label.
    """
    text = " ".join(str(name).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def load_evident():
    """Import ``evident`` from the cloned skill scripts.

    Returns
    -------
    module
        The evident-charts matplotlib helper.

    Raises
    ------
    FileNotFoundError
        When the clone is missing. The message includes the clone command.
    """
    if not EVIDENT_CHARTS_SCRIPTS_DIR.is_dir():
        raise FileNotFoundError(
            "git clone --depth 1 https://github.com/rhiever/evident-charts.git /tmp/evident-charts"
        )
    scripts = str(EVIDENT_CHARTS_SCRIPTS_DIR)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import evident

    return evident
