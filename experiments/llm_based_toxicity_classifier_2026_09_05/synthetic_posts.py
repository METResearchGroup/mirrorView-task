"""Build synthetic social media posts for the LLM toxicity smoke test.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from faker import Faker
from pydantic import BaseModel

FAKER_LOCALE = "en_US"
CLEAN_SENTENCE_WORD_COUNT = 12
INJECTED_BASE_WORD_COUNT = 8
SOURCE_RECORD_ID_PREFIX = "synthetic_"
SOURCE_RECORD_ID_WIDTH = 5
MEDIUM_TOXIC_PHRASES = (
    "You're an idiot and this is a dumb take.",
    "Shut up, nobody asked you.",
    "That comment is pathetic and you sound clueless.",
    "What a loser. Sit this one out.",
)
HIGH_TOXIC_PHRASES = (
    "People like you should be wiped off the map.",
    "Go kill yourself, you worthless garbage.",
    "I hope you get hurt and never come back.",
    "You're subhuman and don't deserve to exist.",
)
InjectedTier = Literal["medium", "high"]
PHRASES_BY_TIER: dict[InjectedTier, tuple[str, ...]] = {
    "medium": MEDIUM_TOXIC_PHRASES,
    "high": HIGH_TOXIC_PHRASES,
}


class SyntheticPost(BaseModel):
    """One synthetic smoke-test post, including whether toxic language was injected."""

    source_record_id: str
    text: str
    toxicity_was_injected: bool
    injected_tier: InjectedTier | None


@dataclass(frozen=True)
class InjectionAssignment:
    """Which post index receives which injected toxic phrase."""

    index: int
    tier: InjectedTier
    phrase: str


def build_synthetic_posts(
    post_count: int,
    injected_toxic_count: int,
    seed: int,
) -> list[SyntheticPost]:
    """Build Faker posts and inject toxic language into a random subset.

    Parameters
    ----------
    post_count
        Number of posts to build.
    injected_toxic_count
        How many of those posts receive injected toxic language.
    seed
        Seed for Faker and for choosing which posts are injected.

    Returns
    -------
    list[SyntheticPost]
        Posts with ids, text, and injection flags.

    Raises
    ------
    ValueError
        When ``injected_toxic_count`` is outside ``[0, post_count]``.
    """
    _require_inject_count_in_range(post_count, injected_toxic_count)
    fake = Faker(FAKER_LOCALE)
    fake.seed_instance(seed)
    rng = random.Random(seed)
    slots = _injection_slots(post_count, injected_toxic_count, rng)
    return [_post_for_slot(index, fake, slots[index]) for index in range(post_count)]


def _require_inject_count_in_range(post_count: int, injected_toxic_count: int) -> None:
    if injected_toxic_count < 0 or injected_toxic_count > post_count:
        raise ValueError(
            f"injected_toxic_count must be in [0, {post_count}], got {injected_toxic_count}"
        )


def _injection_slots(
    post_count: int,
    injected_toxic_count: int,
    rng: random.Random,
) -> list[InjectionAssignment | None]:
    slots: list[InjectionAssignment | None] = [None] * post_count
    if injected_toxic_count == 0:
        return slots
    chosen_indexes = rng.sample(range(post_count), injected_toxic_count)
    medium_count = injected_toxic_count // 2
    for offset, index in enumerate(chosen_indexes):
        tier: InjectedTier = "medium" if offset < medium_count else "high"
        phrases = PHRASES_BY_TIER[tier]
        slots[index] = InjectionAssignment(
            index=index,
            tier=tier,
            phrase=phrases[offset % len(phrases)],
        )
    return slots


def _post_for_slot(
    index: int,
    fake: Faker,
    assignment: InjectionAssignment | None,
) -> SyntheticPost:
    if assignment is None:
        return _clean_post(index, fake)
    return _injected_post(index, fake, assignment)


def _source_record_id(index: int) -> str:
    return f"{SOURCE_RECORD_ID_PREFIX}{index:0{SOURCE_RECORD_ID_WIDTH}d}"


def _clean_post(index: int, fake: Faker) -> SyntheticPost:
    return SyntheticPost(
        source_record_id=_source_record_id(index),
        text=fake.sentence(nb_words=CLEAN_SENTENCE_WORD_COUNT),
        toxicity_was_injected=False,
        injected_tier=None,
    )


def _injected_post(
    index: int,
    fake: Faker,
    assignment: InjectionAssignment,
) -> SyntheticPost:
    base_text = fake.sentence(nb_words=INJECTED_BASE_WORD_COUNT)
    return SyntheticPost(
        source_record_id=_source_record_id(index),
        text=f"{base_text} {assignment.phrase}",
        toxicity_was_injected=True,
        injected_tier=assignment.tier,
    )
