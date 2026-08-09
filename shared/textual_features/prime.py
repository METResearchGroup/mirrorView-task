"""PRIME-cue textual feature classifier (binary any-of).

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.prime import PrimeClassification"
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

PRIME_EXAMPLES = '\n## Examples\n\nPost: "Senator X is a national hero and everyone should follow her lead."\nAnswer: 1\n\nPost: "I made coffee and read emails this morning."\nAnswer: 0\n\nPost: "People like us are being ignored again while their side gets everything."\nAnswer: 1\n\nPost: "The city council passed a transportation budget."\nAnswer: 0\n\nPost: "It is disgusting and immoral what they did to those families."\nAnswer: 1\n\nPost: "The weather is mild today and traffic is normal."\nAnswer: 0\n'

PRIME_SYSTEM_PROMPT = '\nYou are a helpful assistant. Your task is to classify whether a single social media post contains PRIME content.\n\n## Definition\n\nPRIME content includes one or more of:\n- Prestigious cues (status/success/authority signals)\n- In-group cues (us-vs-them identity, group affiliation, group boundaries)\n- Moral cues (right/wrong, virtue/vice, norm violations, condemnation/praise)\n- Emotional cues (strong affective language, especially high-arousal emotion)\n\n## Decision rule\n\nOutput "1" if the post contains clear PRIME content (any one of the categories is sufficient).\nOutput "0" if none are clearly present.\n\nUse conservative judgment:\n- If ambiguous or weak, output "0".\n- Factual/neutral reporting without clear PRIME cues should be "0".\n- Only use the text provided; do not infer hidden context.\n\nOnly output your label. ONLY output 0 or 1.\n\n\n## Examples\n\nPost: "Senator X is a national hero and everyone should follow her lead."\nAnswer: 1\n\nPost: "I made coffee and read emails this morning."\nAnswer: 0\n\nPost: "People like us are being ignored again while their side gets everything."\nAnswer: 1\n\nPost: "The city council passed a transportation budget."\nAnswer: 0\n\nPost: "It is disgusting and immoral what they did to those families."\nAnswer: 1\n\nPost: "The weather is mild today and traffic is normal."\nAnswer: 0\n\n'

PRIME_PROMPT = '\n\n\nYou are a helpful assistant. Your task is to classify whether a single social media post contains PRIME content.\n\n## Definition\n\nPRIME content includes one or more of:\n- Prestigious cues (status/success/authority signals)\n- In-group cues (us-vs-them identity, group affiliation, group boundaries)\n- Moral cues (right/wrong, virtue/vice, norm violations, condemnation/praise)\n- Emotional cues (strong affective language, especially high-arousal emotion)\n\n## Decision rule\n\nOutput "1" if the post contains clear PRIME content (any one of the categories is sufficient).\nOutput "0" if none are clearly present.\n\nUse conservative judgment:\n- If ambiguous or weak, output "0".\n- Factual/neutral reporting without clear PRIME cues should be "0".\n- Only use the text provided; do not infer hidden context.\n\nOnly output your label. ONLY output 0 or 1.\n\n\n## Examples\n\nPost: "Senator X is a national hero and everyone should follow her lead."\nAnswer: 1\n\nPost: "I made coffee and read emails this morning."\nAnswer: 0\n\nPost: "People like us are being ignored again while their side gets everything."\nAnswer: 1\n\nPost: "The city council passed a transportation budget."\nAnswer: 0\n\nPost: "It is disgusting and immoral what they did to those families."\nAnswer: 1\n\nPost: "The weather is mild today and traffic is normal."\nAnswer: 0\n\n\n\nPost: {prompt_input}\nAnswer:\n'


class PrimeClassification(BaseModel):
    """Structured PRIME label for one post."""

    is_prime: bool


_PRIME_PROMPT = ChatPromptTemplate.from_messages(
    [("human", PRIME_PROMPT)]
)


def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    """Build a ChatOpenAI client using ``OPENAI_API_KEY``.

    Parameters
    ----------
    model
        OpenAI model id.

    Returns
    -------
    ChatOpenAI
        Configured LangChain chat model.
    """
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, api_key=api_key)


def classify_post(post: str) -> PrimeClassification:
    """Classify one post via OpenAI structured output (LangChain).

    Parameters
    ----------
    post
        Social media post text.

    Returns
    -------
    PrimeClassification
        Structured ``is_prime`` label.
    """
    llm = get_llm()
    structured = llm.with_structured_output(PrimeClassification)
    chain = _PRIME_PROMPT | structured
    return chain.invoke({"prompt_input": post})


def classify_texts(posts: list[str]) -> list[PrimeClassification]:
    """Classify each post with ``classify_post``.

    Parameters
    ----------
    posts
        Post texts.

    Returns
    -------
    list[PrimeClassification]
        One label per input post.
    """
    return [classify_post(p) for p in tqdm(posts, desc="PRIME classification")]
