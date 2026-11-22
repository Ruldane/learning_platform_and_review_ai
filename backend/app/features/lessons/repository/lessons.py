import builtins
from datetime import datetime

from sqlalchemy import ColumnElement, CursorResult, and_, case, func, literal, or_, select, update

from app.db.models.agents import AgentSession
from app.db.models.lessons import Lesson
from app.db.models.program import Module, Program
from app.db.repository import UserScopedRepository


class LessonRepository(UserScopedRepository[Lesson]):
    """Leçons d'un utilisateur, une par module. Lectures fraîches (`populate_existing`) : sous le
    verrou des leçons d'un programme, une requête voit ce que la précédente a commité."""

    model = Lesson

    async def ready_for_conversation(
        self,
        terms: builtins.list[str],
        previous: builtins.list[str],
        limit: int,
        *,
        followed_only: bool = False,
    ) -> builtins.list[Lesson]:
        """Leçons publiées des programmes de ce compte, d’abord par correspondance textuelle."""
        score: ColumnElement[int] = literal(0)
        for term in terms:
            score = (
                score
                + case((func.lower(Lesson.title).contains(term, autoescape=True), 4), else_=0)
                + case((func.lower(Program.title).contains(term, autoescape=True), 2), else_=0)
                + case((func.lower(Lesson.markdown).contains(term, autoescape=True), 1), else_=0)
            )
        owned = (
            select(Lesson)
            .join(Module, Module.id == Lesson.module_id)
            .join(Program, Program.id == Lesson.program_id)
            .where(
                Lesson.user_id == self.user_id,
                Lesson.status == "ready",
                Program.user_id == self.user_id,
                Module.user_id == self.user_id,
                Module.program_id == Program.id,
                Module.skipped.is_(False),
            )
        )
        if followed_only:
            owned = owned.where(Program.status == "validated")
        if terms:
            found = (
                await self.session.scalars(
                    owned.where(score > 0).order_by(score.desc(), Lesson.id).limit(limit)
                )
            ).all()
            if found:
                return builtins.list(found)
        if not previous:
            return []
        by_id = {
            lesson.id: lesson
            for lesson in await self.session.scalars(owned.where(Lesson.id.in_(previous)))
        }
        return [by_id[lesson_id] for lesson_id in previous if lesson_id in by_id][:limit]

    async def get_fresh(self, lesson_id: str) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.id == lesson_id, Lesson.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def set_pdf_key(self, lesson_id: str, key: str, session_id: str | None = None) -> bool:
        """Range le PDF si la leçon n'en a pas encore ; `False` sinon (déjà rangé, ou leçon
        disparue). Une écriture technique : `updated_at` garde l'instant où la leçon est devenue
        prête, que le fil d'activité date (D173)."""
        scope = [Lesson.id == lesson_id, Lesson.user_id == self.user_id, Lesson.pdf_key.is_(None)]
        if session_id is not None:
            scope.append(Lesson.session_id == session_id)
        stmt = update(Lesson).where(*scope).values(pdf_key=key, updated_at=Lesson.updated_at)
        result = await self.session.execute(stmt)
        return isinstance(result, CursorResult) and result.rowcount == 1

    async def claim_published(self, lesson_id: str, session_id: str) -> bool:
        """Autorise la suite d'une publication tant que la même version reste publiée."""
        stmt = (
            update(Lesson)
            .where(
                Lesson.user_id == self.user_id,
                Lesson.id == lesson_id,
                Lesson.session_id == session_id,
                Lesson.status == "ready",
            )
            .values(updated_at=Lesson.updated_at)
            .returning(Lesson.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def claim_verification(
        self, module_id: str, session_id: str, *, replay: bool = False
    ) -> Lesson | None:
        """Prend le verrou d'écriture SQLite avant de lire le brouillon à publier ou refuser.

        L'annulation MCP et l'annulation moteur prennent ce même verrou. Si elles passent
        d'abord, la session n'a plus l'autorisation de publier, même avec un checkpoint.
        """
        eligible = Lesson.verification_session_id == session_id
        if replay:
            eligible = or_(
                eligible,
                and_(
                    Lesson.verification_session_id.is_(None),
                    Lesson.session_id == session_id,
                    Lesson.status == "ready",
                ),
            )
        running = (
            select(AgentSession.id)
            .where(
                AgentSession.id == session_id,
                AgentSession.user_id == self.user_id,
                AgentSession.status == "running",
            )
            .exists()
        )
        stmt = (
            update(Lesson)
            .where(Lesson.user_id == self.user_id, Lesson.module_id == module_id, eligible, running)
            .values(updated_at=Lesson.updated_at)
            .returning(Lesson)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_module(self, module_id: str) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.user_id == self.user_id, Lesson.module_id == module_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_program(self, program_id: str) -> builtins.list[Lesson]:
        stmt = (
            select(Lesson)
            .where(Lesson.user_id == self.user_id, Lesson.program_id == program_id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def recent_settled(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> builtins.list[Lesson]:
        """Les leçons prêtes ou en échec dont le dernier changement est dans `[after, before]`
        (bornes incluses), plus récentes d'abord (fil d'activité)."""
        stmt = select(Lesson).where(
            Lesson.user_id == self.user_id, Lesson.status.in_(("ready", "failed"))
        )
        if after is not None:
            stmt = stmt.where(Lesson.updated_at >= after)
        if before is not None:
            stmt = stmt.where(Lesson.updated_at <= before)
        stmt = stmt.order_by(Lesson.updated_at.desc(), Lesson.id.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars())
