"""Professor preferences and token usage (10.A3): the mode (automatic or on demand), the style
(`guide` or pair), the idle timer, the session and day caps. Usage is read from the call log
(`TeacherUsageRepository`): the code session's tokens and those of the user's day (her time zone,
D98). No text is read."""

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
        """The saved preferences, otherwise the defaults (100,000 tokens per session, 300,000 per
        day, automatic mode, guide style)."""
        row = await PreferenceRepository(self._db, self._user_id).mine()
        if row is None:
            return PreferencesOut()
        return PreferencesOut.model_validate(row)

    async def save_preferences(self, data: PreferencesIn) -> PreferencesOut:
        """Replaces the preferences (one row per account)."""
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
        """The professor's tokens: for the session (0 when no session is given) and the day, the
        caps, and whether the professor is "on demand" (by choice, or cap reached)."""
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
