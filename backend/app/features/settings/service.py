import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.run_settings import RunSettings
from app.features.settings.delays import DEFAULT_DELAYS as DEFAULT_DELAYS
from app.features.settings.delays import validated_delays as validated_delays
from app.features.settings.repository import UserSettingsRepository
from app.features.settings.schemas import UserSettings, is_overridable
from app.providers.llm.base import ModelChoice, Tier

logger = logging.getLogger(__name__)

# Les champs calculés sont recalculés à la lecture : on ne les stocke pas.
_COMPUTED = {"availability": {"weekly_budget_minutes"}}


def _has_removed_agents(stored: dict[str, Any]) -> bool:
    overrides = stored.get("agent_overrides")
    return isinstance(overrides, dict) and not all(is_overridable(name) for name in overrides)


def _without_removed_agents(stored: dict[str, Any]) -> dict[str, Any]:
    """Retire d'une surcharge stockée un agent qui n'est plus au catalogue (renommé, supprimé,
    de démonstration) : les autres surcharges restent. Ne journalise rien : les réglages se lisent
    à chaque appel de modèle ; `SettingsService.replace` le dit une fois, à l'enregistrement."""
    if not _has_removed_agents(stored):
        return stored
    overrides: dict[str, Any] = stored["agent_overrides"]
    kept = {name: choice for name, choice in overrides.items() if is_overridable(name)}
    return {**stored, "agent_overrides": kept}


def _parse_stored(stored: dict[str, Any]) -> UserSettings:
    """Défauts fusionnés avec le stocké. Les clés inconnues sont ignorées (compatibilité
    ascendante) ; un champ invalide retombe sur son défaut sans faire échouer la lecture."""
    stored = _without_removed_agents(stored)
    try:
        return UserSettings.model_validate(stored)
    except ValidationError as exc:
        invalid = {str(err["loc"][0]) for err in exc.errors() if err["loc"]}
        # Seuls les noms de champs sont journalisés, jamais leur contenu.
        logger.warning("Réglages stockés invalides, valeurs par défaut pour : %s", sorted(invalid))
        kept = {key: value for key, value in stored.items() if key not in invalid}
        try:
            return UserSettings.model_validate(kept)
        except ValidationError:
            return UserSettings()


class SettingsService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._repo = UserSettingsRepository(session, user_id)

    async def get(self, *, initialize: bool = False) -> UserSettings:
        """Les réglages stockés, défauts fusionnés ; ne fait aucune écriture, sauf `initialize`.

        `initialize` (réservé à `GET /settings` et à `replace`) : au tout premier accès d'un compte
        sans ligne de réglages, crée la ligne qui fixe `onboarding_done` : vrai si le compte a déjà
        une clé d'API ou un objectif (compte d'avant la phase 9, D183), faux sinon. La décision est
        prise une fois, jamais refaite : une clé ajoutée pendant le premier lancement ne le termine
        pas. Les autres lecteurs (autres features, agents, tâches planifiées) ne passent pas
        `initialize` : une écriture dans leur lecture garderait le verrou d'écriture de la base
        pendant qu'une autre session écrit.
        """
        stored = await self._repo.get_data()
        if stored is None and initialize:
            stored = await self._repo.initialize(
                {"onboarding_done": await self._repo.has_prior_data()}
            )
        return _parse_stored(stored if isinstance(stored, dict) else {})

    async def replace(self, new: UserSettings) -> UserSettings:
        """Enregistre les réglages. `onboarding_done` ne repasse jamais à faux : une page qui
        renvoie l'ancien réglage (ou l'oublie) ne rouvre pas le premier lancement (P20). Le
        dépôt l'écrit de façon monotone (pas de lecture puis écriture) : même deux requêtes qui
        se croisent ne le défont pas ; la réponse dit ce qui est enregistré."""
        current = await self.get(initialize=True)
        stored = await self._repo.get_data() or {}
        if _has_removed_agents(stored):
            # Une fois, ici : la surcharge d'un agent disparu part avec ce remplacement.
            logger.warning(
                "Réglages enregistrés : surcharge d'un agent disparu retirée (agent_overrides)"
            )
        done = current.onboarding_done or new.onboarding_done
        kept = new.model_copy(update={"onboarding_done": done})
        await self._repo.save_data(kept.model_dump(mode="json", exclude=_COMPUTED))
        saved = await self._repo.get_data() or {}
        return kept.model_copy(update={"onboarding_done": bool(saved.get("onboarding_done", done))})


class SettingsModelReader:
    """Lecture du modèle à utiliser, pour la fabrique LLM. Ouvre sa propre session : elle est
    appelée hors requête HTTP (agents, tâches planifiées)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        async with self._session_factory() as session:
            settings = await SettingsService(session, user_id).get()
        if agent is not None and agent in settings.agent_overrides:
            return settings.agent_overrides[agent]
        return settings.tiers[tier]


class SettingsRunReader:
    """Réglages d'une exécution d'agents (`RunSettingsSource` du moteur), assemblé par
    `app.bootstrap`. Ouvre sa propre session : appelé par le runner, hors requête HTTP."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_run_settings(self, user_id: str) -> RunSettings:
        async with self._session_factory() as session:
            settings = await SettingsService(session, user_id).get()
        return RunSettings(
            session_token_cap=settings.session_token_cap,
            debate_rounds=settings.debate_rounds,
            lesson_language=settings.lesson_language,
            search_languages=tuple(settings.search_languages),
            style_guide=settings.style_guide,
        )
