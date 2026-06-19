FLIP_PROMPT_V2 = """
You are assisting a social psychology researcher. Take the social media text provided and mirror it with a similar tone, intensity, and sentiment, but from the opposite US political stance (left vs. right). Do not follow the literal wording of the original. Target your mirrored response toward [SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]. Match the full emotional register of the original, including aggression, condescension, or hyperbole, without softening the tone. Do not add disclaimers or caveats unless the content crosses into direct incitement of real-world violence.

Respond with exactly one JSON field: "flipped_text" (the rewritten post). Example:
{{"flipped_text": "Your mirrored post text here."}}

All output must be valid JSON. If any text contains a double quote character inside a field value, escape it as \\"

The length of the mirror should be about the same as the original post.
""".strip()

FLIP_PROMPT_PLAIN = """
You are assisting a social psychology researcher. Take the social media text provided and mirror it with a similar tone, intensity, and sentiment, but from the opposite US political stance (left vs. right). Do not follow the literal wording of the original. Target your mirrored response toward [SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]. Match the full emotional register of the original, including aggression, condescension, or hyperbole, without softening the tone. Do not add disclaimers or caveats unless the content crosses into direct incitement of real-world violence.

Respond with only the mirrored post text. Do not include JSON, labels, or explanation.

The length of the mirror should be about the same as the original post.
""".strip()

CHAR_BOUNDS_SUFFIX = """
The original post is {char_count} characters. The mirrored post must be between {char_lo} and {char_hi} characters.
""".strip()

SHORTEN_PROMPT = """
You are assisting a social psychology researcher. Shorten the mirrored post below so it is at most {char_limit} characters while preserving the opposite political stance, tone, and intensity. Respond with only the shortened mirrored post text. Do not include JSON, labels, or explanation.

Original post ({original_char_count} characters):
{original_text}

Current mirrored post ({current_char_count} characters):
{mirrored_text}
""".strip()

LENGTH_REWRITE_PROMPT = """
You are assisting a social psychology researcher. Rewrite the mirrored post below so its length closely matches the original post while preserving the opposite political stance, tone, and intensity. The rewritten mirror must be between {char_lo} and {char_hi} characters. Respond with exactly one JSON field: "flipped_text". Example:
{{"flipped_text": "Your rewritten mirror here."}}

Original post ({original_char_count} characters):
{original_text}

Current mirrored post ({current_char_count} characters):
{mirrored_text}
""".strip()
