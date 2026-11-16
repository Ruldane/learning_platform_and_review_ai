"""Port du parcours `daily_brief` (`BriefStore`, D161) sur la feature `brief` : implémentation
branchée par `bootstrap_agents.agent_ports(..., brief=...)`. Chaque appel ouvre sa propre session de
base, courte.

`context` relit le brief : les faits du conseil sont tirés des rubriques du code (jamais recomptés
ici), le sujet de la ressource est « {domaine visé} actualités » (`service.topic` : poste du radar,
poste de l'objectif, sujet tiré de son texte, titre du programme validé ; rien : `None`, aucune
recherche), les nombres permis dans le conseil sont ceux des faits (`advice_numbers`, en chiffres).
Les écritures sont **conditionnelles et idempotentes** (SPEC 9.4) : la ressource ne s'écrit que si
elle est encore absente (`WHERE resource IS NULL`), le conseil que s'il est encore `pending` ; la
première écriture gagne, y compris un conseil `None` (`failed` ou `unavailable`), qui reste donc
tel toute la journée. Journaux : identifiants et nombres ; jamais un fait, un sujet, une ressource
ni une phrase (17.2)."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any, Literal

from app.agents.tools.brief_port import AdviceFacts, BriefContext
from app.agents.tools.brief_schema import ResourceView
from app.features.brief.repository import BriefRepository
from app.features.brief.service.rules import advice_numbers
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.topic import resource_topic
from app.features.brief.service.views import brief_not_found
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


def facts_of(sections: dict[str, Any]) -> AdviceFacts:
    """Les faits du jour tels que les rubriques du brief les disent : le bloc, les fiches de la
    file, les relances dues, les offres montrées, la semaine (sans programme : zéros). Le fait d'une
    rubrique en panne (`unavailable`) est `None` : jamais un zéro inventé pour le conseil."""
    down = frozenset(sections.get("unavailable", ()))
    block: dict[str, Any] | None = sections.get("block")
    week: dict[str, Any] = sections.get("week") or {}

    def known(name: str, value: int) -> int | None:
        return None if name in down else value

    return AdviceFacts(
        block_title=block["lesson_title"] if block else None,
        block_minutes=known("block", block["minutes"] if block else 0),
        cards_due=known("reviews", sections["reviews"]["queue"]),
        reminders_due=known("reminders", sections["reminders"]["due"]),
        offers=known("offers", len(sections["offers"]["items"])),
        best_score=week.get("best_quiz"),
        week_planned=known("week", week.get("tasks_total", 0)),
        week_done=known("week", week.get("tasks_done", 0)),
        streak_days=known("week", week.get("streak_days", 0)),
    )


def allowed_numbers(facts: AdviceFacts) -> frozenset[str]:
    """Les nombres que le conseil peut citer : ceux des faits, en chiffres seulement."""
    return frozenset(
        advice_numbers(
            {
                "minutes": facts.block_minutes,
                "cards": facts.cards_due,
                "reminders": facts.reminders_due,
                "offers": facts.offers,
                "score": facts.best_score,
                "planned": facts.week_planned,
                "done": facts.week_done,
                "streak": facts.streak_days,
            }
        )
    )


class AgentBriefStore:
    def __init__(self, runtime: BriefRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, brief_id: str) -> BriefContext:
        async with self._rt.session_factory() as db:
            row = await BriefRepository(db, user_id).get_fresh(brief_id)
            if row is None:
                raise brief_not_found()
            settings = await SettingsService(db, user_id).get()
            topic = await resource_topic(db, user_id)
        facts = facts_of(row.sections)
        language: Literal["fr", "en"] = "en" if settings.lesson_language == "en" else "fr"
        return BriefContext(
            brief_id=row.id,
            day=row.day,
            language=language,
            topic=topic,
            facts=facts,
            resource_done=row.resource is not None,
            advice_done=row.advice_status != "pending",
            allowed_numbers=allowed_numbers(facts),
        )

    async def _written(
        self, user_id: str, brief_id: str, write: Callable[[BriefRepository], Awaitable[bool]]
    ) -> bool:
        """Applique l'écriture `write(repo)` ; 404 si le brief n'est pas à cette utilisatrice."""
        async with self._rt.session_factory() as db:
            repo = BriefRepository(db, user_id)
            written = await write(repo)
            await db.commit()
            if not written and await repo.get(brief_id) is None:
                raise brief_not_found()
        return written

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None:
        data: dict[str, Any] = asdict(resource) if resource is not None else {}
        written = await self._written(user_id, brief_id, lambda r: r.save_resource(brief_id, data))
        logger.info(
            "Ressource rangée : session %s, brief %s, première écriture %s, vide %s",
            session_id,
            brief_id,
            written,
            resource is None,
        )

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None:
        if sentences is not None:
            sentences_data = {"sentences": list(sentences)}
            written = await self._written(
                user_id, brief_id, lambda r: r.save_advice(brief_id, sentences_data)
            )
        else:
            status = "unavailable" if unavailable else "failed"
            written = await self._written(
                user_id, brief_id, lambda r: r.close_advice(brief_id, status)
            )
        logger.info(
            "Conseil rangé : session %s, brief %s, première écriture %s, écrit %s",
            session_id,
            brief_id,
            written,
            sentences is not None,
        )
