import logging

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import UserSettingsRow
from app.features.settings.repository import UserSettingsRepository
from app.features.settings.schemas import Availability, UserSettings, WeeklyReview
from app.features.settings.service import SettingsModelReader, SettingsService
from app.providers.llm.base import ModelChoice
from app.providers.llm.model_defaults import GLM_STRONG


async def test_defaults_when_nothing_stored(db_session: AsyncSession) -> None:
    s = await SettingsService(db_session, "u1").get()
    assert s.debate_rounds == 3 and s.session_token_cap == 300_000
    assert s.reminder_delays_days == [7, 14, 21] and s.brief_time == "07:00"
    assert all(
        c == ModelChoice(provider="anthropic", model="claude-haiku-5-5") for c in s.tiers.values()
    )
    assert s.availability.weekly_budget_minutes == 840


async def test_spec_defaults(db_session: AsyncSession) -> None:
    s = await SettingsService(db_session, "u1").get()
    assert s.availability == Availability(
        weekday_minutes=120, weekend_block_min_minutes=180, weekend_block_max_minutes=240
    )
    assert s.weekly_review == WeeklyReview(day="sunday", time="18:00")
    assert s.lesson_language == "fr" and s.search_languages == ["fr", "en"]
    assert s.style_guide == "" and s.preferred_domains == [] and s.excluded_domains == []
    assert s.agent_overrides == {} and s.search_provider_order == ["searxng", "brave"]


async def test_replace_persists_and_is_isolated(db_session: AsyncSession) -> None:
    s = await SettingsService(db_session, "u1").get()
    await SettingsService(db_session, "u1").replace(s.model_copy(update={"debate_rounds": 5}))
    assert (await SettingsService(db_session, "u1").get()).debate_rounds == 5
    assert (await SettingsService(db_session, "u2").get()).debate_rounds == 3


async def test_replace_twice_keeps_one_row(db_session: AsyncSession) -> None:
    service = SettingsService(db_session, "u1")
    s = await service.get()
    await service.replace(s.model_copy(update={"debate_rounds": 2}))
    await service.replace(s.model_copy(update={"debate_rounds": 4}))
    assert (await service.get()).debate_rounds == 4
    assert len(await UserSettingsRepository(db_session, "u1").list()) == 1


async def test_unknown_stored_key_is_ignored(db_session: AsyncSession) -> None:
    await UserSettingsRepository(db_session, "u1").save_data(
        {"debate_rounds": 4, "champ_futur": {"a": 1}}
    )
    s = await SettingsService(db_session, "u1").get()
    assert s.debate_rounds == 4 and not hasattr(s, "champ_futur")


async def test_invalid_stored_field_falls_back_to_default_for_that_field(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    await UserSettingsRepository(db_session, "u1").save_data(
        {"debate_rounds": 99, "brief_time": "06:30", "style_guide": "secret-style-content-xyz"}
    )
    with caplog.at_level(logging.WARNING):
        s = await SettingsService(db_session, "u1").get()
    assert s.debate_rounds == 3  # champ invalide : défaut
    assert s.brief_time == "06:30"  # champs valides conservés
    assert s.style_guide == "secret-style-content-xyz"
    assert "debate_rounds" in caplog.text and "secret-style-content-xyz" not in caplog.text


async def test_repository_assigns_new_dict_and_scopes_by_user(db_session: AsyncSession) -> None:
    repo = UserSettingsRepository(db_session, "u1")
    assert await repo.get_data() is None
    await repo.save_data({"debate_rounds": 2})
    first = (await repo.list())[0]
    assert isinstance(first, UserSettingsRow)
    data_before = first.data
    await repo.save_data({"debate_rounds": 4})
    assert first.data is not data_before and first.data == {"debate_rounds": 4}
    assert await UserSettingsRepository(db_session, "u2").get_data() is None


@pytest.mark.parametrize("value", ["7:00", "24:00", "07:60", "0700", "ab:cd", "07:00 "])
def test_hours_must_be_hh_mm(value: str) -> None:
    with pytest.raises(ValidationError):
        UserSettings(brief_time=value)
    with pytest.raises(ValidationError):
        WeeklyReview(time=value)


@pytest.mark.parametrize(
    "bad", [{"debate_rounds": 0}, {"debate_rounds": 6}, {"session_token_cap": 9_999}]
)
def test_bounds_are_enforced(bad: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        UserSettings.model_validate(bad)


async def test_agent_override_wins(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = SettingsService(db_session, "u1")
    s = await service.get()
    glm = ModelChoice(provider="glm", model=GLM_STRONG)
    await service.replace(s.model_copy(update={"agent_overrides": {"strategist": glm}}))
    await db_session.commit()
    reader = SettingsModelReader(db_session_factory)
    assert (await reader.get_model_choice("u1", "fort", "strategist")).provider == "glm"
    assert (await reader.get_model_choice("u1", "fort", None)).provider == "anthropic"
    assert (await reader.get_model_choice("u1", "fort", "autre")).provider == "anthropic"
    # Un autre utilisateur n'est pas affecté par la surcharge.
    assert (await reader.get_model_choice("u2", "fort", "strategist")).provider == "anthropic"
