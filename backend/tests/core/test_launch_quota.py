"""Le plafond de lancements de parcours par le MCP (M11) : au plus `limit` par utilisatrice sur
24 h glissantes ; un lancement qui échoue avant d'avoir démarré rend sa place."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.core.launch_quota import GRAPH_LAUNCHES_PER_DAY, LaunchQuota

T0 = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)


def test_default_limit_is_thirty_per_day() -> None:
    assert GRAPH_LAUNCHES_PER_DAY == 30 and LaunchQuota().limit == 30


def test_refuses_after_the_limit_in_french_without_content() -> None:
    quota = LaunchQuota(limit=3)
    for i in range(3):
        quota.reserve("u1", T0 + timedelta(minutes=i))
    with pytest.raises(AppError) as caught:
        quota.reserve("u1", T0 + timedelta(minutes=5))
    error = caught.value
    assert error.code == "mcp_graph_quota" and error.status_code == 429
    assert "3 workflow launches" in error.message
    assert error.details == {"limit": 3, "window": "day"}


def test_the_day_is_rolling_and_per_user() -> None:
    quota = LaunchQuota(limit=2)
    quota.reserve("u1", T0)
    quota.reserve("u1", T0 + timedelta(hours=1))
    quota.reserve("u2", T0 + timedelta(hours=1))  # une autre utilisatrice : son propre compte
    with pytest.raises(AppError):
        quota.reserve("u1", T0 + timedelta(hours=23))
    quota.reserve("u1", T0 + timedelta(hours=24, minutes=1))  # le premier est sorti de la fenêtre


def test_a_refusal_does_not_count_and_a_released_place_is_given_back() -> None:
    quota = LaunchQuota(limit=1)
    place = quota.reserve("u1", T0)
    with pytest.raises(AppError):
        quota.reserve("u1", T0 + timedelta(minutes=1))
    with pytest.raises(AppError):
        quota.reserve("u1", T0 + timedelta(minutes=2))  # le refus n'a rien consommé
    quota.release("u1", place)
    quota.reserve("u1", T0 + timedelta(minutes=3))
