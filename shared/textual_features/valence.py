"""Valence (positive / not-positive) textual feature classifier.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.valence import ValenceClassification"
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

BINARY_SENTIMENT_PROMPT = '\nYou are a sentiment analysis expert. Your task is to determine whether the overall valence of the following social media post is positive.\n\nInstructions:\n- If the post expresses a favorable attitude, optimism, praise, or generally good feelings, classify as true.\n- If the post expresses criticism, disapproval, pessimism, anger, or generally bad feelings, classify as false.\n- Consider the overall tone, affect, and language of the post.\n- If there is a mix of positive and negative language, use the dominant sentiment.\n- Ignore sarcasm unless it is obvious.\n- Do NOT classify as "neutral". Every post should be labeled as true (positive) or false (not positive).\n\nFew-shot Examples:\n\nExample 1:\nPost: "I really enjoyed reading this, it made my day better!"\nis_positive: true\n\nExample 2:\nPost: "This is awful. I can\'t believe people think this way."\nis_positive: false\n\nExample 3:\nPost: "Beautifully written and very inspiring."\nis_positive: true\n\nExample 4:\nPost: "This post is misleading and frustrating to read."\nis_positive: false\n\nNow, given the following post, reply strictly in this JSON format:\n\n{{\n  "is_positive": <true|false>\n}}\n\nPost:\n"""{post}"""\n'


class ValenceClassification(BaseModel):
    """Structured valence label for one post."""

    is_positive: bool


_VALENCE_PROMPT = ChatPromptTemplate.from_messages(
    [("human", BINARY_SENTIMENT_PROMPT)]
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


def classify_post(post: str) -> ValenceClassification:
    """Classify one post via OpenAI structured output (LangChain).

    Parameters
    ----------
    post
        Social media post text.

    Returns
    -------
    ValenceClassification
        Structured ``is_positive`` label.
    """
    llm = get_llm()
    structured = llm.with_structured_output(ValenceClassification)
    chain = _VALENCE_PROMPT | structured
    return chain.invoke({"post": post})


def classify_texts(posts: list[str]) -> list[ValenceClassification]:
    """Classify each post with ``classify_post``.

    Parameters
    ----------
    posts
        Post texts.

    Returns
    -------
    list[ValenceClassification]
        One label per input post.
    """
    return [classify_post(p) for p in tqdm(posts, desc="Valence classification")]
