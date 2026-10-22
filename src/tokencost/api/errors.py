"""Every error response uses one envelope: {"error": {"code", "message", "details"}}."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from tokencost.core.service import ModelNotFoundError


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code, content=body.model_dump(exclude_none=True)
    )


def _status_code_slug(status_code: int) -> str:
    return HTTPStatus(status_code).phrase.lower().replace(" ", "_").replace("-", "_")


async def _model_not_found(_: Request, exc: Exception) -> JSONResponse:
    return error_response(404, "model_not_found", str(exc))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Report where and why, but never echo the submitted input back.
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return error_response(
        422, "validation_error", "Request validation failed.", details
    )


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return error_response(
        exc.status_code, _status_code_slug(exc.status_code), str(exc.detail)
    )


async def _unhandled_error(_: Request, __: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ModelNotFoundError, _model_not_found)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Unknown model"},
    422: {"model": ErrorResponse, "description": "Invalid request"},
}
