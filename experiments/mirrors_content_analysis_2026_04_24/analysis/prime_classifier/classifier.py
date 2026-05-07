"""PRIME classifier for MirrorView run data.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader
from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

PRIME_EXAMPLES = """
## Examples

Post: "Senator X is a national hero and everyone should follow her lead."
Answer: 1

Post: "I made coffee and read emails this morning."
Answer: 0

Post: "People like us are being ignored again while their side gets everything."
Answer: 1

Post: "The city council passed a transportation budget."
Answer: 0

Post: "It is disgusting and immoral what they did to those families."
Answer: 1

Post: "The weather is mild today and traffic is normal."
Answer: 0
"""

PRIME_SYSTEM_PROMPT = f"""
You are a helpful assistant. Your task is to classify whether a single social media post contains PRIME content.

## Definition

PRIME content includes one or more of:
- Prestigious cues (status/success/authority signals)
- In-group cues (us-vs-them identity, group affiliation, group boundaries)
- Moral cues (right/wrong, virtue/vice, norm violations, condemnation/praise)
- Emotional cues (strong affective language, especially high-arousal emotion)

## Decision rule

Output "1" if the post contains clear PRIME content (any one of the categories is sufficient).
Output "0" if none are clearly present.

Use conservative judgment:
- If ambiguous or weak, output "0".
- Factual/neutral reporting without clear PRIME cues should be "0".
- Only use the text provided; do not infer hidden context.

Only output your label. ONLY output 0 or 1.

{PRIME_EXAMPLES}
"""

PRIME_PROMPT = f"""

{PRIME_SYSTEM_PROMPT}

Post: {{prompt_input}}
Answer:
"""


class PrimeClassification(BaseModel):
    is_prime: bool


_PRIME_PROMPT = ChatPromptTemplate.from_messages(
    [("human", PRIME_PROMPT)]
)

PRIME_CLASSIFIER_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = PRIME_CLASSIFIER_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = PRIME_CLASSIFIER_DIR / "labels_mirrors.csv"


def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, api_key=api_key)


def classify_post(post: str) -> PrimeClassification:
    """Classify one post via OpenAI structured output (LangChain)."""
    llm = get_llm()
    structured = llm.with_structured_output(PrimeClassification)
    chain = _PRIME_PROMPT | structured
    return chain.invoke({"prompt_input": post})


def classify_texts(posts: list[str]) -> list[PrimeClassification]:
    """Classify each post with `classify_post`."""
    return [classify_post(p) for p in tqdm(posts, desc="PRIME classification")]


def _all_mirrors_claude_path() -> Path:
    return Dataloader.PROJECT_ROOT / "img" / "all_mirrors_claude.csv"


def _build_posts_frame(raw: pd.DataFrame, text_column: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_primary_key": raw["post_primary_key"].astype(str),
            "text": raw[text_column].fillna("").astype(str),
        }
    )


def _label_posts_dataframe(posts: pd.DataFrame) -> pd.DataFrame:
    texts = posts["text"].tolist()
    classifications = classify_texts(texts)
    return pd.DataFrame(
        {
            "post_primary_key": posts["post_primary_key"].tolist(),
            "is_prime": [c.is_prime for c in classifications],
        }
    )


def classify_posts() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load Claude mirrors CSV, classify both text columns, and write label CSVs."""
    path = _all_mirrors_claude_path()
    raw = pd.read_csv(path)
    for col in ("post_primary_key", "original_text", "claude_mirror"):
        if col not in raw.columns:
            raise KeyError(f"Expected column {col!r} in {path}")

    original_posts = _build_posts_frame(raw, "original_text")
    mirrored_posts = _build_posts_frame(raw, "claude_mirror")

    labels_original = _label_posts_dataframe(original_posts)
    labels_mirrors = _label_posts_dataframe(mirrored_posts)

    labels_original.to_csv(LABELS_ORIGINAL_PATH, index=False)
    labels_mirrors.to_csv(LABELS_MIRRORS_PATH, index=False)
    return labels_original, labels_mirrors


if __name__ == "__main__":
    classify_posts()
