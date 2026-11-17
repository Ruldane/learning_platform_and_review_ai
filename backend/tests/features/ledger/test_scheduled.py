"""Les comptes que traitent les tâches planifiées (D197) : ceux dont le premier lancement est fini,
la même règle que `GET /settings` (D183)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import ApiKey, User, UserSettingsRow
from app.db.models.learning import Goal
from app.features.ledger.service.ledger import scheduled_user_ids
from app.features.settings.service import SettingsService


async def test_scheduled_user_ids_follow_the_first_launch_rule_of_get_settings(
    db_session: AsyncSession,
) -> None:
    """Un compte ne prend de passage que si `GET /settings` le dit « fait » (D183, D197) : le test
    compare la liste à `onboarding_done` de chaque compte, lu comme la route le lit."""
    fresh, done, undone, keyed, goaled, old_row = (
        "neuf",
        "fait",
        "ouvert",
        "cle",
        "objectif",
        "ancien",
    )
    accounts = [fresh, done, undone, keyed, goaled, old_row]
    db_session.add_all([User(id=name, user_id=name) for name in accounts])
    db_session.add_all(
        [
            UserSettingsRow(user_id=done, data={"onboarding_done": True}),
            UserSettingsRow(user_id=undone, data={"onboarding_done": False}),
            # Ligne d'avant la phase 9 : la migration 0015 y a posé `onboarding_done = true`.
            UserSettingsRow(user_id=old_row, data={"debate_rounds": 3, "onboarding_done": True}),
            ApiKey(user_id=keyed, provider="glm", encrypted_key="chiffre", last4="abcd"),
            Goal(user_id=goaled, text="Devenir ingénieure en apprentissage automatique"),
            # Des données mais une ligne `onboarding_done = false` : la porte le garde à l'accueil.
            Goal(user_id=undone, text="Devenir ingénieure en apprentissage automatique"),
        ]
    )
    await db_session.commit()
    listed = await scheduled_user_ids(db_session)
    assert sorted(listed) == sorted([done, keyed, goaled, old_row])
    for name in accounts:
        route = (await SettingsService(db_session, name).get(initialize=True)).onboarding_done
        assert (name in listed) is route


async def test_scheduled_user_ids_read_nothing_for_an_empty_space(db_session: AsyncSession) -> None:
    assert await scheduled_user_ids(db_session) == []
