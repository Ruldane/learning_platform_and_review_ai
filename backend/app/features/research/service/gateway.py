"""Passerelle web des agents (D77) : implémente le port `WebGateway` de `app.agents` sur le service
de recherche. Chaque appel ouvre ses propres sessions de base, courtes (D66) ; la recherche et la
lecture d'une session passent sous son verrou (`searching`, `reading`), donc un nœud rejoué ne
recompte rien et ne dédouble aucune source.

Journaux : identifiants seulement, jamais une requête, une URL ni un titre (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from typing import get_args

from app.agents.tools.web_port import (
    CRITERIA_MAX,
    PageRead,
    PersonFound,
    SourceVerdictView,
    WebHit,
    WebLimits,
    WebSearchResult,
)
from app.db.models.research import PageStatus
from app.features.research.service.people import record_person
from app.features.research.service.prefs import load_prefs
from app.features.research.service.reading import (
    Judged,
    PageOutcome,
    read,
    record_verdict,
    session_verdicts,
)
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import SearchOutcome, search
from app.providers.search.base import TimeRange

logger = logging.getLogger(__name__)

_TIME_RANGES: tuple[str, ...] = get_args(TimeRange)


def _time_range(value: str | None) -> TimeRange | None:
    """Une période inconnue est ignorée (le modèle peut en inventer une) plutôt que refusée."""
    return value if value in _TIME_RANGES else None  # type: ignore[return-value]


def _search_result(outcome: SearchOutcome) -> WebSearchResult:
    hits = [
        WebHit(
            title=ranked.result.title,
            url=ranked.result.url,
            snippet=ranked.result.snippet,
            engine=ranked.result.engine,
            published=ranked.result.published,
            preferred=ranked.preferred,
        )
        for ranked in outcome.hits
    ]
    return WebSearchResult(query=outcome.query, provider=outcome.provider, hits=hits)


def _view(source_id: str, judged: Judged) -> SourceVerdictView:
    return SourceVerdictView(
        source_id=source_id,
        score=judged.score,
        verdict=judged.verdict,
        reason=judged.reason,
        summary=judged.summary,
    )


def _verdict(outcome: PageOutcome) -> SourceVerdictView | None:
    """Verdict déjà posé dans la session (D82) : `judge` le réémet sans rappeler le modèle."""
    judged = outcome.judged
    if judged is None or outcome.source_id is None:
        return None
    return _view(outcome.source_id, judged)


def _page(outcome: PageOutcome) -> PageRead:
    status: PageStatus = outcome.status
    return PageRead(
        source_id=outcome.source_id,
        url=outcome.url,
        status=status,
        title=outcome.title,
        text=outcome.text,
        author=outcome.author,
        date=outcome.date,
        lang=outcome.lang,
        reason=outcome.reason,
        verdict=_verdict(outcome),
    )


def _detail(criteria: dict[str, int]) -> dict[str, int]:
    """Points par critère, chacun borné à son barème (10.3) ; une clé inconnue ne compte pas. La
    note sur 100 est la somme : le modèle ne donne jamais le total."""
    return {
        name: max(0, min(maximum, criteria.get(name, 0))) for name, maximum in CRITERIA_MAX.items()
    }


class AgentWebGateway:
    def __init__(self, runtime: ResearchRuntime) -> None:
        self._runtime = runtime

    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> WebSearchResult:
        outcome = await search(
            self._runtime,
            user_id,
            session_id,
            query,
            lang=lang,
            time_range=_time_range(time_range),
            categories=categories,
        )
        return _search_result(outcome)

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        return _page(await read(self._runtime, user_id, session_id, url))

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        """Enregistre la note et le verdict (idempotent : un nœud rejoué écrit la même chose).
        `criteria=None` : écartée sans note (note impossible à établir). `source_not_found`
        (404) si la source n'est pas à l'utilisateur."""
        detail = None if criteria is None else _detail(criteria)
        async with self._runtime.session_factory() as db:
            source = await record_verdict(
                db,
                user_id,
                source_id,
                score=None if detail is None else sum(detail.values()),
                detail=detail,
                reason=reason,
                summary=summary,
            )
            await db.commit()
            view = SourceVerdictView(
                source_id=source.id,
                score=source.score,
                verdict="kept" if source.verdict == "kept" else "rejected",
                reason=source.reason or "",
                summary=source.summary or "",
            )
        logger.info(
            "Source notée : utilisateur %s, session %s, source %s, %s",
            user_id,
            session_id,
            source_id,
            view.verdict,
        )
        return view

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        """Verdicts déjà posés (filtrés par utilisateur et session) parmi `source_ids`."""
        wanted = set(source_ids)
        if not wanted:
            return {}
        async with self._runtime.session_factory() as db:
            known = await session_verdicts(db, user_id, session_id)
        return {sid: _view(sid, judged) for sid, judged in known.items() if sid in wanted}

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        """Praticien enregistré dans les sources de la session (idempotent), sous le verrou de
        la session comme une lecture : deux écritures de la même personne n'en font qu'une."""
        lock = self._runtime.session_lock(user_id, session_id)
        async with lock, self._runtime.session_factory() as db:
            source = await record_person(db, user_id, session_id, person)
            await db.commit()
            return source.id

    async def limits(self, user_id: str) -> WebLimits:
        async with self._runtime.session_factory() as db:
            prefs = await load_prefs(db, user_id)
        return WebLimits(
            languages=prefs.languages,
            preferred=prefs.preferred,
            max_queries=prefs.max_queries,
            max_pages=prefs.max_pages,
        )
