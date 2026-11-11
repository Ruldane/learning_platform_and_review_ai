import anthropic
import httpx
import openai
import pytest

from app.core.errors import AppError
from app.providers.llm.errors import is_transient

REQUEST = httpx.Request("POST", "https://exemple.test/v1/messages")


def response(status: int) -> httpx.Response:
    return httpx.Response(status, request=REQUEST)


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ReadTimeout("t"),
        httpx.ConnectError("c"),
        httpx.RemoteProtocolError("p"),
        ConnectionResetError("r"),
        TimeoutError("t"),
        httpx.HTTPStatusError("429", request=REQUEST, response=response(429)),
        httpx.HTTPStatusError("503", request=REQUEST, response=response(503)),
        anthropic.APITimeoutError(request=REQUEST),
        anthropic.APIConnectionError(request=REQUEST),
        anthropic.RateLimitError("x", response=response(429), body=None),
        anthropic.InternalServerError("x", response=response(500), body=None),
        anthropic.APIStatusError("surchargé", response=response(529), body=None),
        openai.APITimeoutError(request=REQUEST),
        openai.APIConnectionError(request=REQUEST),
        openai.RateLimitError("x", response=response(429), body=None),
        openai.InternalServerError("x", response=response(502), body=None),
    ],
)
def test_transient_errors(exc: BaseException) -> None:
    assert is_transient(exc)


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("x"),
        KeyError("x"),
        AppError("llm_key_missing", "x"),
        httpx.HTTPStatusError("400", request=REQUEST, response=response(400)),
        anthropic.AuthenticationError("x", response=response(401), body=None),
        anthropic.BadRequestError("x", response=response(400), body=None),
        openai.AuthenticationError("x", response=response(401), body=None),
        openai.BadRequestError("x", response=response(400), body=None),
    ],
)
def test_non_transient_errors(exc: BaseException) -> None:
    assert not is_transient(exc)
