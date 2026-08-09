"""Intergroup-discussion textual feature classifier.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.intergroup import IntergroupClassification"
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

INTERGROUP_EXAMPLES = '\n## Examples\n\nPost: "Customers are upset because the management changed the return policy."\nAnswer: 1\n\nPost: "She was frustrated after missing her bus."\nAnswer: 0\n\nPost: "People in City A say City B always cheats during football tournaments."\nAnswer: 1\n\nPost: "Members of my hiking club disagreed on where to set up camp."\nAnswer: 0\n\nPost: "Why do older employees ignore what the younger staff suggest?"\nAnswer: 1\n\nPost: "A new bakery opened across from the old one."\nAnswer: 0\n\nPost: "Several men argued loudly outside the bar."\nAnswer: 0\n'

INTERGROUP_SYSTEM_PROMPT = '\nYou are a helpful assistant. Your job is to analyze a single social media post and answer a binary classification question\n\n## Task\n\nDecide whether the post involves intergroup discussion. In social psychology, intergroup refers to interactions or situations that involve two or more groups that define themselves—or are defined by others—as distinct based on characteristics such as identity, beliefs, status, affiliation, or other boundaries.\n\n- If you judge that the post describes, reports, or implies intergroup discussion, respond with: "1"\n- If the post is unrelated, speaks only about individuals, is ambiguous, or describes within-group matters, respond with: "0"\n\nOnly output your label. ONLY output 0 or 1.\n\n\n## Examples\n\nPost: "Customers are upset because the management changed the return policy."\nAnswer: 1\n\nPost: "She was frustrated after missing her bus."\nAnswer: 0\n\nPost: "People in City A say City B always cheats during football tournaments."\nAnswer: 1\n\nPost: "Members of my hiking club disagreed on where to set up camp."\nAnswer: 0\n\nPost: "Why do older employees ignore what the younger staff suggest?"\nAnswer: 1\n\nPost: "A new bakery opened across from the old one."\nAnswer: 0\n\nPost: "Several men argued loudly outside the bar."\nAnswer: 0\n\n'

INTERGROUP_PROMPT = '\n\n\nYou are a helpful assistant. Your job is to analyze a single social media post and answer a binary classification question\n\n## Task\n\nDecide whether the post involves intergroup discussion. In social psychology, intergroup refers to interactions or situations that involve two or more groups that define themselves—or are defined by others—as distinct based on characteristics such as identity, beliefs, status, affiliation, or other boundaries.\n\n- If you judge that the post describes, reports, or implies intergroup discussion, respond with: "1"\n- If the post is unrelated, speaks only about individuals, is ambiguous, or describes within-group matters, respond with: "0"\n\nOnly output your label. ONLY output 0 or 1.\n\n\n## Examples\n\nPost: "Customers are upset because the management changed the return policy."\nAnswer: 1\n\nPost: "She was frustrated after missing her bus."\nAnswer: 0\n\nPost: "People in City A say City B always cheats during football tournaments."\nAnswer: 1\n\nPost: "Members of my hiking club disagreed on where to set up camp."\nAnswer: 0\n\nPost: "Why do older employees ignore what the younger staff suggest?"\nAnswer: 1\n\nPost: "A new bakery opened across from the old one."\nAnswer: 0\n\nPost: "Several men argued loudly outside the bar."\nAnswer: 0\n\n\n\nPost: {prompt_input}\nAnswer:\n'


class IntergroupClassification(BaseModel):
    """Structured intergroup label for one post."""

    is_intergroup: bool


_INTERGROUP_PROMPT = ChatPromptTemplate.from_messages(
    [("human", INTERGROUP_PROMPT)]
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


def classify_post(post: str) -> IntergroupClassification:
    """Classify one post via OpenAI structured output (LangChain).

    Parameters
    ----------
    post
        Social media post text.

    Returns
    -------
    IntergroupClassification
        Structured ``is_intergroup`` label.
    """
    llm = get_llm()
    structured = llm.with_structured_output(IntergroupClassification)
    chain = _INTERGROUP_PROMPT | structured
    return chain.invoke({"prompt_input": post})


def classify_texts(posts: list[str]) -> list[IntergroupClassification]:
    """Classify each post with ``classify_post``.

    Parameters
    ----------
    posts
        Post texts.

    Returns
    -------
    list[IntergroupClassification]
        One label per input post.
    """
    return [classify_post(p) for p in tqdm(posts, desc="Intergroup classification")]
