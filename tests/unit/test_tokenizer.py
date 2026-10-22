from tokencost.core.tokenizer import APPROXIMATION_ENCODING, count_tokens


def test_counts_tokens_and_characters() -> None:
    result = count_tokens("Hello world, how many tokens is this sentence?")

    assert result.characters == 46
    assert result.tokens == 10
    assert result.method == "approximate"
    assert result.tokenizer == APPROXIMATION_ENCODING


def test_empty_text_is_zero_tokens() -> None:
    assert count_tokens("").tokens == 0


def test_special_token_strings_are_treated_as_plain_text() -> None:
    # Must not raise, and must not collapse into a single special token.
    assert count_tokens("<|endoftext|>").tokens > 1
