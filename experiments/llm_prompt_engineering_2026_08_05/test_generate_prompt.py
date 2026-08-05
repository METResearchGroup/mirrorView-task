"""Smoke-check generate_prompt with and without the keep/remove features addendum.

Run from repo root:
  PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/test_generate_prompt.py
"""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.generate_prompt import generate_prompt

POST_1 = (
    "I'm a bleeding-heart liberal, and I think the issue of abortion is "
    "obviously about protecting women's rights!"
)
POST_2 = (
    "I'm a staunch conservative, and abortion is fully about the sanctity "
    "of human life before birth!"
)


def main() -> None:
    without_addendum = generate_prompt(
        post_1_text=POST_1,
        post_2_text=POST_2,
        add_keep_remove_features_addendum=False,
    )
    with_addendum = generate_prompt(
        post_1_text=POST_1,
        post_2_text=POST_2,
        add_keep_remove_features_addendum=True,
    )

    print("=" * 72)
    print("add_keep_remove_features_addendum=False")
    print("=" * 72)
    print(without_addendum)
    print()
    print("=" * 72)
    print("add_keep_remove_features_addendum=True")
    print("=" * 72)
    print(with_addendum)


if __name__ == "__main__":
    main()
