import anthropic
import httpx
import openai
import pytest

from app.core.errors import AppError
from app.providers.llm.errors import describe_provider_error, is_transient

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


# --- Erreurs lisibles (I3) -----------------------------------------------------------------

LEAKY = "Incorrect API key provided: sk-proj-****cdef. Corps brut du fournisseur."


def _status_error(cls: type, status: int, code: str | None = None) -> BaseException:
    """Erreur de SDK comme la construit le client : `body` = contenu de `{"error": ...}`."""
    body = {"code": code, "message": LEAKY} if code else None
    return cls(LEAKY, response=response(status), body=body)  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("exc", "provider", "label", "code", "fragment"),
    [
        (
            _status_error(openai.AuthenticationError, 401),
            "openai",
            "OpenAI",
            "llm_key_rejected",
            "Clé refusée par OpenAI",
        ),
        (
            _status_error(anthropic.PermissionDeniedError, 403),
            "anthropic",
            "Anthropic",
            "llm_key_rejected",
            "Clé refusée par Anthropic",
        ),
        (
            _status_error(openai.RateLimitError, 429, "1113"),
            "glm",
            "GLM (Z.ai)",
            "llm_credit_exhausted",
            "Crédit Z.ai insuffisant",
        ),
        (
            _status_error(openai.RateLimitError, 429, "1305"),
            "glm",
            "GLM (Z.ai)",
            "llm_rate_limited",
            "Service Z.ai surchargé",
        ),
        (
            _status_error(openai.RateLimitError, 429, "insufficient_quota"),
            "openai",
            "OpenAI",
            "llm_credit_exhausted",
            "Crédit OpenAI épuisé",
        ),
        (
            _status_error(openai.RateLimitError, 429),
            "openai",
            "OpenAI",
            "llm_rate_limited",
            "Limite de requêtes ou crédit épuisé chez OpenAI",
        ),
        (
            _status_error(openai.InternalServerError, 503),
            "glm",
            "GLM (Z.ai)",
            "llm_unavailable",
            "GLM (Z.ai) est indisponible",
        ),
        (
            _status_error(anthropic.APIStatusError, 529),
            "anthropic",
            "Anthropic",
            "llm_unavailable",
            "Anthropic est indisponible",
        ),
        (
            _status_error(openai.BadRequestError, 400),
            "openai",
            "OpenAI",
            "llm_request_rejected",
            "OpenAI a refusé la requête (400)",
        ),
        (
            openai.APITimeoutError(request=REQUEST),
            "openai",
            "OpenAI",
            "llm_timeout",
            "OpenAI n'a pas répondu à temps",
        ),
        (
            httpx.ReadTimeout(LEAKY),
            None,
            "le fournisseur",
            "llm_timeout",
            "le fournisseur n'a pas répondu à temps",
        ),
        (
            openai.APIConnectionError(request=REQUEST),
            "glm",
            "GLM (Z.ai)",
            "llm_unavailable",
            "Impossible de joindre GLM (Z.ai)",
        ),
        (
            httpx.HTTPStatusError(LEAKY, request=REQUEST, response=response(401)),
            None,
            "X",
            "llm_key_rejected",
            "Clé refusée par X",
        ),
    ],
)
def test_provider_errors_become_readable_french_messages(
    exc: BaseException, provider: str | None, label: str, code: str, fragment: str
) -> None:
    error = describe_provider_error(exc, provider=provider, label=label)
    assert error is not None
    assert error.code == code
    assert fragment in error.message
    # Jamais le message brut du SDK (il cite parfois la fin de la clé) ni le corps de réponse.
    assert "cdef" not in error.message and "Corps brut" not in error.message
    assert "cdef" not in str(error.details) and "Corps brut" not in str(error.details)


@pytest.mark.parametrize(
    "exc", [ValueError("x"), RuntimeError("x"), AppError("token_cap_reached", "Plafond.")]
)
def test_other_errors_are_not_provider_errors(exc: BaseException) -> None:
    assert describe_provider_error(exc, provider="openai", label="OpenAI") is None


def test_exhausted_credit_is_not_retried_but_overload_is() -> None:
    assert not is_transient(_status_error(openai.RateLimitError, 429, "1113"))
    assert not is_transient(_status_error(openai.RateLimitError, 429, "insufficient_quota"))
    assert is_transient(_status_error(openai.RateLimitError, 429, "1305"))
