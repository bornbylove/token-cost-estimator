from fastapi import APIRouter

from tokencost.api.errors import ERROR_RESPONSES
from tokencost.core.schemas import TokenCountRequest, TokenCountResult
from tokencost.core.tokenizer import count_tokens

router = APIRouter(prefix="/tokens", tags=["tokens"], responses=ERROR_RESPONSES)


@router.post("/count")
def count_text_tokens(request: TokenCountRequest) -> TokenCountResult:
    """Approximate the number of tokens in a piece of text. The text is not stored."""
    return count_tokens(request.text)
