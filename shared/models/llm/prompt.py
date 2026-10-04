"""Issue 351 optimized Study 2 keep or remove prompt.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.llm.prompt import format_optimized_study_prompt"
"""

from __future__ import annotations

OPTIMIZED_STUDY_PROMPT_TEMPLATE = """You are reviewing a pair of political mirror posts for a political social media platform. The posts express analogous messages from opposing viewpoints and are not replies. Apply the same standards regardless of ideology, party, candidate, movement, or protected characteristic.

Decide whether the pair supports healthy political discussion.

Allow substantive political speech, including criticism of politicians, parties, policies, institutions, and movements; claims that policies cause harm; and forceful, blunt, or emotional disagreement.

Remove if either post contains:
- Targeted hostile abuse, harassment, threats, calls for harm, dehumanization, or degrading/contemptuous language.
- Sweeping attacks on political groups or their members.
- Obscene, aggressively dismissive, taunting, mocking, or inflammatory language directed at opponents or their views.
- Unsupported assertions or insinuations that a named person committed serious criminal, sexual, or similarly grave misconduct. A bare accusation is not protected political criticism merely because it concerns a public figure.

Distinguish criticism from abuse:
- Allow criticism focused on actions, policies, consequences, public statements, or documented conduct, when not abusively framed.
- Remove language whose main effect is to insult, humiliate, provoke hostility toward, or contemptuously dismiss a political person, group, or viewpoint.
- Do not remove solely for strong political disagreement. Remove only when abusive, threatening, degrading, inflammatory, or gravely accusatory as described above.

Make one binary decision for the pair:
- Allow only if both posts should remain.
- Remove if either post should be removed.

Here are examples of pairs of posts that human annotators remove:

1. Post 1: Conservative Christians are on the side of the capitalist class or billionaires and should be physically fought. #communism #socialism Post 2: Radical leftists are on the side of the globalist elites and government tyrants and should be physically fought. #MAGA #freedom

2. Post 1: Fuck this smug DNC-groomed hypocrite. The day he actually fights for the Second Amendment will be the first day, since he's been kissing up to nothing but coastal elites and radical activists who want to strip law-abiding citizens of their rights entirely (see AOC and her defund-the-police crowd). Post 2: Fuck this entitled GOP raised asshole. The day he's a force in the fight for gun control will be the first day since he kisses up to nothing but entitled white men who have no issue with guns at all (see Bernie and the Nazi).

3. Post 1: Woke, DEI, social justice, critical race theory, politically correct, civil rights, restorative justice, reparations... Just use the hard R, this is taking forever Post 2: MAGA, Christian nationalism, originalism, states' rights, traditional values, heritage, America First, constitutional conservatism... Just say white supremacy, this is taking forever

4. Post 1: And why there are far fewer soy-brained libtard town hall meetings to 'splain why Biden's corruption and cognitive decline is good for them . . they don't want to be held accountable, the spineless cowards .. Post 2: And why there are far fewer cuckservative Rethuglicunt town hall meetings to 'splain why #Trump 's fuckery and criminal behavior is good for them . . they don't want to be yelled at, the spineless cowards ..

5. Post 1: Democrats will never be an honest decent party with integrity, generosity, and warmth – it's all about grasping for power and quite a bit about exploiting the vulnerable! Post 2: Republicans will never be an honest decent party with integrity generosity and warmth – it's all about cold hard cash and quite a bit about raping children!


Here are examples of pairs of posts that human annotators keep:

1. Post 1: If everyone who says something to the effect of "gun rights are important for hunters" understood how stupid the average Wisconsinite hunter is - and how drunk they get by 7am with guns in hand - we would not have gun ownership in this country Post 2: If everyone who says something to the effect of "we need stricter gun control" understood how absolutely clueless the average coastal liberal is about firearms - and how they've never touched a gun in their life yet lecture everyone about them - we would not take gun grabbers seriously in this

2. Post 1: For decades the US left told us we shouldn't impose American values on other 
countries — sovereignty matters, they said. But now they're falling all over themselves to copy Europe's socialist failures: crushing taxes, open borders, and state-controlled speech. Post 2: For decades we were told by the US rightwing that we shouldn't look to other countries in how to run things (healthcare, gun safety, and consumer regulations were proposed) but the rightwing is all in in emulating Hungary under Orban. To paraphrase Clinton: "it's the authoritarianism, stupid."

3. Post 1: always under siege Second Amendment. Lloyd Smucker has my Complete and Total Endorsement for Re-Election. Election Day is Tuesday, May 19th. GET OUT AND VOTE FOR LLOYD — HE WILL NEVER LET YOU DOWN! Post 2: They never stop coming for your right to choose. Planned Parenthood PAC has my Complete and Total Endorsement for every candidate fighting to protect reproductive freedom. Election Day is Tuesday, November 5th. GET OUT AND VOTE FOR CHOICE — THESE CANDIDATES WILL NEVER LET YOU DOWN!

4. Post 1: The Secretary of State should be charged with voter suppression by making it harder for working people to cast their ballots in person. Expand mail voting now. Post 2: The Postmaster General of the US should be charged with violation of law by breaking down the mail ballot system. Go vote in person

5. Post 1: I take exception to some of how the definition of "assault weapon" is formed. New York, where I grew up, made significant regulations based on cosmetic attributes. Post 2: I take exception to how the right keeps pretending 'assault weapon' is impossible to define. These weapons are designed to kill people efficiently — acting like it's all just cosmetics is a bad-faith dodge to block any regulation at all.

Post 1: {post_1_text}

Post 2: {post_2_text}

Return only the decision.

keep or remove
"""

_POST_1_PLACEHOLDER = "{post_1_text}"
_POST_2_PLACEHOLDER = "{post_2_text}"


def format_optimized_study_prompt(post_1_text: str, post_2_text: str) -> str:
    """Render the optimized prompt with unchanged post text.

    Parameters
    ----------
    post_1_text
        Original-side post text inserted at the first placeholder.
    post_2_text
        Mirror-side post text inserted at the second placeholder.

    Returns
    -------
    str
        Prompt text with only the two post placeholders substituted.

    Raises
    ------
    ValueError
        When either placeholder is missing or repeated in the template.
    """
    template = OPTIMIZED_STUDY_PROMPT_TEMPLATE
    if template.count(_POST_1_PLACEHOLDER) != 1 or template.count(_POST_2_PLACEHOLDER) != 1:
        raise ValueError("optimized prompt must contain each post placeholder once")
    rendered = template.replace(_POST_1_PLACEHOLDER, post_1_text, 1)
    return rendered.replace(_POST_2_PLACEHOLDER, post_2_text, 1)
