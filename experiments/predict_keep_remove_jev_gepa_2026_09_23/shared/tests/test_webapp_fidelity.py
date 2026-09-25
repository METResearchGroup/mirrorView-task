"""Fidelity tests against linked-fate webapp instruction copy."""

from __future__ import annotations

import re

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    CLOSING_LINE,
    STUDY_INSTRUCTION,
    render_pair_prompt,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.prompt import (
    STUDY_INSTRUCTION as REASONING_STUDY_INSTRUCTION,
)

# Literal linked-fate instruction strings from webapp/public/main.js lines 607-620.
WEBAPP_LINKED_FATE_HTML_SNIPPETS = (
    """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. 
                            Your task will be to review a series of <b>pairs</b> of real political social media posts, and decide whether <b>both posts in the pair</b> should be <b>allowed</b> or <b>removed</b> from the platform.</p>""",
    """<p>The pairs are <b>political mirrors</b> of each other. This means that the mirror text <b>recreates the original message</b> from the <b>opposite political stance</b>. For example:</p>""",
    """<p><b>Original Text:</b><br>
                           <i>I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!</i></p>""",
    """<p><b>Mirror Text:</b><br>
                           <i>I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!</i></p>""",
    """<p>Notice that the mirror text changes the core message to match that of the opposite political stance.
                              In other words, the mirror text is <b>not a response to the original text</b> - it replicates the original message as if written from the opposite political stance.</p>""",
    """<p>Your job is to decide whether <b>both posts in the pair</b> should be <b>allowed</b> or <b>removed</b> from the platform.</p>""",
    """<p>When making your decisions, consider generally whether a post contributes to a <b>healthy environment for political discussion</b>, or whether it would be <b>unhealthy for political discussion</b>. Your goal is to evaluate the messages, using your own judgment.</p>""",
    """<p>There are no right or wrong answers - we are interested in what you personally think.</p>""",
)


def _strip_html(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    without_tags = re.sub(r"\s+([.!?,;:])", r"\1", without_tags)
    return re.sub(r"\s+", " ", without_tags).strip()


def _webapp_instruction_sentences() -> list[str]:
    sentences: list[str] = []
    for snippet in WEBAPP_LINKED_FATE_HTML_SNIPPETS:
        plain = _strip_html(snippet)
        for part in re.split(r"(?<=[.!?])\s+", plain):
            cleaned = part.strip()
            if cleaned and "Click Next" not in cleaned:
                sentences.append(cleaned)
    return sentences


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class TestWebappFidelity:
    def test_rendered_pair_prompt_matches_webapp_linked_fate_copy(self) -> None:
        rendered = render_pair_prompt("o", "m", "original", add_criteria=False)
        normalized_rendered = _normalize_whitespace(rendered)

        for sentence in _webapp_instruction_sentences():
            assert _normalize_whitespace(sentence) in normalized_rendered

        assert rendered.endswith("Allow or Remove?")
        assert STUDY_INSTRUCTION == REASONING_STUDY_INSTRUCTION
        assert "Allow Or Remove?" not in rendered
