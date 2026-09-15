"""Prompt rendering for the four experiment ablations."""

from __future__ import annotations

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
)

REFLECTION_QUESTION = (
    "You just completed a series of content moderation decisions where you saw "
    "pairs of posts expressing opposing political viewpoints on the same topic - "
    "one from a left-leaning perspective and one from a right-leaning perspective - "
    "and made a single joint decision about both. In a few sentences, please "
    "describe what was going through your mind as you made these decisions. What, "
    "if anything, influenced how you evaluated the posts as a pair?"
)

STUDY_SYSTEM_PROMPT = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.

The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.

Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

There are no right or wrong answers - we are interested in what you personally think.

You will see all 20 post pairs at once in the user message. Return a JSON object with remove_pair_indexes: a list of 1-indexed pair numbers to remove. An empty list means keep all pairs."""

DEMOGRAPHIC_FIELDS: tuple[tuple[str, str], ...] = (
    ("age", "Age"),
    ("gender", "Gender"),
    ("education", "Education"),
    ("political_affiliation", "Political affiliation"),
    ("party_lean", "Party lean"),
    ("party_group", "Party group"),
    (
        "political_ideology",
        "Political ideology (1 = Extremely liberal, 7 = Extremely conservative)",
    ),
    (
        "political_follow",
        "How closely do you follow politics (1 = Not closely at all, 7 = Very closely)",
    ),
    (
        "rep_id",
        "I identify with the Republican Party (1 = Fully Disagree, 7 = Fully agree)",
    ),
    (
        "dem_id",
        "I identify with the Democratic Party (1 = Fully Disagree, 7 = Fully agree)",
    ),
    (
        "attitude_reduce_abortion",
        "Reducing access to abortion (0 = Strongly Oppose, 100 = Strongly Support)",
    ),
    (
        "attitude_citizenship_undocumented",
        "Providing a path to citizenship for undocumented immigrants (0 to 100)",
    ),
    (
        "attitude_restrict_guns",
        "Increasing restrictions on gun ownership (0 to 100)",
    ),
    (
        "attitude_regulate_environment",
        "Increasing government regulations to protect the environment (0 to 100)",
    ),
    (
        "attitude_raise_wealth_taxes",
        "Raising taxes on the wealthiest Americans (0 to 100)",
    ),
    (
        "attitude_expand_medicaid",
        "Expanding Medicaid to cover all currently uninsured Americans (0 to 100)",
    ),
)


def render_pairs(trials: list[CohortTrial]) -> str:
    """Render all post pairs for one user."""
    blocks: list[str] = []
    for trial in sorted(trials, key=lambda item: item.pair_index):
        first_text, second_text = _texts_for_pair_order(trial)
        blocks.append(
            f"## Post pair {trial.pair_index}\n\nPost 1:\n{first_text}\n\nPost 2:\n{second_text}"
        )
    return "\n\n".join(blocks)


def render_demographics(user: CohortUser) -> str:
    """Render non-empty demographic and attitude fields."""
    bullets = _demographic_bullets(user)
    if not bullets:
        return ""
    header = (
        "## Participant information\n\n"
        "The following answers were provided by the participant whose keep/remove "
        "choices you are simulating. Use them if they help you match that "
        "participant's decisions.\n\n"
    )
    return header + "\n".join(bullets)


def render_reflection(user: CohortUser) -> str:
    """Render the reflection question, answer, and influence rating."""
    return (
        "## Participant reflection\n\n"
        f"{REFLECTION_QUESTION}\n\n"
        f"Answer: {user.phase1_pair_reflection_text}\n\n"
        "To what extent did seeing both versions of each post influence your "
        f"decisions? (1 = Not at all, 7 = Very much): "
        f"{user.phase1_pair_influence_rating}"
    )


def render_user_prompt(
    experiment_number: int,
    user: CohortUser,
    trials: list[CohortTrial],
) -> str:
    """Render the user prompt for one experiment ablation."""
    sections: list[str] = []
    if experiment_number in (2, 4):
        demo = render_demographics(user)
        if demo:
            sections.append(demo)
    if experiment_number in (3, 4):
        sections.append(render_reflection(user))
    sections.append(render_pairs(trials))
    return "\n\n".join(section for section in sections if section)


def _texts_for_pair_order(trial: CohortTrial) -> tuple[str, str]:
    role_to_text = {
        "original": trial.original_text,
        "mirror": trial.mirror_text,
    }
    return role_to_text[trial.pair_order[0]], role_to_text[trial.pair_order[1]]


def _demographic_bullets(user: CohortUser) -> list[str]:
    bullets: list[str] = []
    for field_name, label in DEMOGRAPHIC_FIELDS:
        value = str(getattr(user, field_name)).strip()
        if value:
            bullets.append(f"- {label}: {value}")
    return bullets
