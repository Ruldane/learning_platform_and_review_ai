"""Les limites d'appels du MCP (P17), par jeton : 429 lisible avec `retry_after`."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.mcp.limits import Limits, RateLimiter
from app.mcp.tools import McpGate
from tests.mcp.support import FakeDispatcher, Mcp

T0 = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)


def identity(token_id: str = "t1") -> McpIdentity:
    return McpIdentity(
        user_id="u1", token_id=token_id, label="Claude", features=frozenset(), mode="write"
    )


async def refused(limiter: RateLimiter, level: int, now: datetime, **kw: str) -> AppError:
    with pytest.raises(AppError) as caught:
        await limiter.check(identity(), level, now, **kw)  # type: ignore[arg-type]
    return caught.value


async def test_rate_limit_per_minute_and_per_day_429_readable() -> None:
    limiter = RateLimiter()
    for i in range(60):
        await limiter.check(identity(), 1, T0 + timedelta(seconds=i * 0.5))

    error = await refused(limiter, 1, T0 + timedelta(seconds=30))

    assert error.status_code == 429 and error.code == "rate_limited"
    assert error.details is not None and 1 <= error.details["retry_after"] <= 60
    assert "60 appels par minute" in error.message and "Réessaie dans" in error.message
    # La minute suivante, ça repasse.
    await limiter.check(identity(), 1, T0 + timedelta(seconds=61))

    daily = RateLimiter(Limits(calls_per_minute=10_000))
    for i in range(1_000):
        await daily.check(identity(), 1, T0 + timedelta(seconds=i))
    error = await refused(daily, 1, T0 + timedelta(seconds=1_001))
    assert "1000 appels par jour" in error.message.replace("1 000", "1000")
    assert error.details is not None and error.details["retry_after"] > 3_600
    assert "h" in error.message  # lisible : en heures
    await daily.check(identity(), 1, T0 + timedelta(days=1, seconds=1))


async def test_writes_per_minute_and_per_day() -> None:
    limiter = RateLimiter()
    for i in range(10):
        await limiter.check(identity(), 2, T0 + timedelta(seconds=i))
    error = await refused(limiter, 2, T0 + timedelta(seconds=11))
    assert "10 écritures par minute" in error.message
    await limiter.check(identity(), 1, T0 + timedelta(seconds=12))  # une lecture passe

    wide = RateLimiter(Limits(writes_per_minute=10_000, calls_per_minute=10_000))
    for i in range(100):
        await wide.check(identity(), 2, T0 + timedelta(seconds=i))
    assert "100 écritures par jour" in (await refused(wide, 2, T0 + timedelta(seconds=101))).message


async def test_daily_limits_can_be_switched_off() -> None:
    """D311 : `None` coupe une limite du jour ; celles de la minute restent."""
    limiter = RateLimiter(
        Limits(
            calls_per_minute=10_000,
            writes_per_minute=10_000,
            calls_per_day=None,
            writes_per_day=None,
        )
    )
    for i in range(1_500):
        await limiter.check(identity(), 2, T0 + timedelta(seconds=i))

    minute = RateLimiter(Limits(writes_per_day=None))
    for i in range(10):
        await minute.check(identity(), 2, T0 + timedelta(seconds=i))
    error = await refused(minute, 2, T0 + timedelta(seconds=11))
    assert "10 écritures par minute" in error.message


def test_daily_limits_from_settings_zero_means_none() -> None:
    assert Limits.with_daily(writes_per_day=0, calls_per_day=0) == Limits(
        writes_per_day=None, calls_per_day=None
    )
    assert Limits.with_daily(writes_per_day=100, calls_per_day=1_000) == Limits()
    assert Limits.with_daily(writes_per_day=500, calls_per_day=0).writes_per_day == 500


def test_settings_daily_mcp_limits_default_and_off() -> None:
    from app.config import Settings

    default = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (default.mcp_writes_per_day, default.mcp_calls_per_day) == (100, 1_000)
    off = Settings(_env_file=None, mcp_writes_per_day=0, mcp_calls_per_day=0)  # type: ignore[call-arg]
    assert (off.mcp_writes_per_day, off.mcp_calls_per_day) == (0, 0)
    with pytest.raises(ValueError):
        Settings(_env_file=None, mcp_writes_per_day=-1)  # type: ignore[call-arg]


async def test_level3_daily_request_cap() -> None:
    limiter = RateLimiter()
    for i in range(20):
        # 5 par minute : sous la limite d'écritures de la minute
        await limiter.check(identity(), 3, T0 + timedelta(minutes=i, seconds=1))
    error = await refused(limiter, 3, T0 + timedelta(minutes=21))
    assert "20 demandes à confirmer par jour" in error.message
    await limiter.check(identity(), 2, T0 + timedelta(minutes=22))  # le niveau 2 n'est pas touché
    await limiter.check(identity(), 3, T0 + timedelta(days=1, minutes=1))


async def test_code_runs_per_minute_and_independent_tokens() -> None:
    limiter = RateLimiter()
    await limiter.check(identity(), 2, T0, bucket="code_run")
    await limiter.check(identity(), 2, T0 + timedelta(seconds=1), bucket="code_run")

    error = await refused(limiter, 2, T0 + timedelta(seconds=2), bucket="code_run")

    assert "2 exécutions de code par minute" in error.message
    await limiter.check(identity(), 2, T0 + timedelta(seconds=3))  # un autre outil passe
    await limiter.check(identity("t2"), 2, T0 + timedelta(seconds=3), bucket="code_run")


async def test_a_refused_call_is_not_counted() -> None:
    limiter = RateLimiter(Limits(calls_per_minute=1))
    await limiter.check(identity(), 1, T0)
    for i in range(1, 30):
        await refused(limiter, 1, T0 + timedelta(seconds=i))
    await limiter.check(identity(), 1, T0 + timedelta(seconds=61))


async def test_429_over_http_is_readable(mcp: Mcp, gate: McpGate, inner: FakeDispatcher) -> None:
    object.__setattr__(gate.limiter, "_limits", Limits(calls_per_minute=2))
    token = await mcp.token()
    assert (await mcp.call(token, "postings_list")).status_code == 200
    assert (await mcp.call(token, "postings_list")).status_code == 200

    response = await mcp.call(token, "postings_list")

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "rate_limited" and "Réessaie dans" in error["message"]
    assert error["details"]["retry_after"] >= 1
    assert int(response.headers["retry-after"]) == error["details"]["retry_after"]
    assert len(inner.calls) == 2  # le troisième n'est jamais parti
    # Les appels qui ne sont pas des outils (ping, liste) ne comptent pas.
    assert (await mcp.rpc(token, "tools/list")).status_code == 200
