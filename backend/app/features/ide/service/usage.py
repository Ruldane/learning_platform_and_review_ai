"""Préférences du professeur et consommation de jetons (10.A3) : le mode (automatique ou sur
demande), le style (`guide` ou binôme), la minuterie d'inactivité, les plafonds de séance et du
jour. La consommation se lit dans le journal des appels (`TeacherUsageRepository`) : les jetons
de la séance de code et ceux du jour de l'utilisatrice (son fuseau, D98). Aucun texte n'est lu."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, local_today, user_zone
from app.features.ide.repository import (
    PreferenceRepository,
    SessionRepository,
    TeacherUsageRepository,
)
from app.features.ide.schemas import PreferencesIn, PreferencesOut, UsageOut
from app.features.ide.service.errors import session_not_found
from app.features.settings.service import SettingsService


class UsageService:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._user_id = user_id

    async def preferences(self) -> PreferencesOut:
        """Les préférences enregistrées, sinon les valeurs de départ (100 000 jetons par séance,
        300 000 par jour, mode automatique, style guide)."""
        row = await PreferenceRepository(self._db, self._user_id).mine()
        if row is None:
            return PreferencesOut()
        return PreferencesOut.model_validate(row)

    async def save_preferences(self, data: PreferencesIn) -> PreferencesOut:
        """Remplace les préférences (une ligne par compte)."""
        repo = PreferenceRepository(self._db, self._user_id)
        values = data.model_dump()
        row = await repo.mine()
        if row is None:
            row = await repo.add(**values)
        else:
            for key, value in values.items():
                setattr(row, key, value)
            await self._db.flush()
        return PreferencesOut.model_validate(row)

    async def _day_start(self) -> datetime:
        zone = user_zone((await SettingsService(self._db, self._user_id).get()).timezone)
        return local_moment(local_today(zone), "00:00", zone)

    async def session_tokens(self, ide_session_id: str) -> int:
        return await TeacherUsageRepository(self._db, self._user_id).of_session(ide_session_id)

    async def day_tokens(self) -> int:
        return await TeacherUsageRepository(self._db, self._user_id).since(await self._day_start())

    async def usage(self, ide_session_id: str | None) -> UsageOut:
        """Les jetons du professeur : de la séance (0 sans séance donnée) et du jour, les plafonds,
        et si le professeur est « sur demande » (par choix, ou plafond atteint)."""
        prefs = await self.preferences()
        session_tokens = 0
        if ide_session_id is not None:
            if await SessionRepository(self._db, self._user_id).get(ide_session_id) is None:
                raise session_not_found()
            session_tokens = await self.session_tokens(ide_session_id)
        day_tokens = await self.day_tokens()
        return UsageOut(
            session_tokens=session_tokens,
            day_tokens=day_tokens,
            session_cap=prefs.session_cap,
            day_cap=prefs.day_cap,
            mode_on_demand=prefs.teacher_mode == "on_demand"
            or session_tokens >= prefs.session_cap
            or day_tokens >= prefs.day_cap,
        )
