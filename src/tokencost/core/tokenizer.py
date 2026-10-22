"""Approximate token counting, done locally so submitted text never leaves the app."""

from functools import cache

import tiktoken

from tokencost.core.schemas import TokenCountResult

# No provider publishes an offline tokenizer for the current models, so every
# count uses OpenAI's newest public encoding as a stand-in.
APPROXIMATION_ENCODING = "o200k_base"

APPROXIMATION_NOTE = (
    f"Approximate count using the public {APPROXIMATION_ENCODING} tokenizer. "
    "Each model tokenizes text differently, so actual counts vary; use the "
    "provider's token counting API when you need exact figures."
)


@cache
def _encoding() -> tiktoken.Encoding:
    # Downloads the vocabulary on first use, then reads it from tiktoken's cache.
    return tiktoken.get_encoding(APPROXIMATION_ENCODING)


def count_tokens(text: str) -> TokenCountResult:
    return TokenCountResult(
        characters=len(text),
        # encode_ordinary treats special-token strings like "<|endoftext|>" as text.
        tokens=len(_encoding().encode_ordinary(text)),
        method="approximate",
        tokenizer=APPROXIMATION_ENCODING,
        note=APPROXIMATION_NOTE,
    )
