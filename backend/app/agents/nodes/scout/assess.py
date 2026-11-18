"""Nœuds de l'Éclaireur qui jugent : noter chaque page lue, garder les sources retenues en mémoire,
résumer. La note vient de cinq critères bornés par le schéma ; le code additionne et applique le
seuil de 60 (la passerelle enregistre, SPEC 10.3)."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.func import task

from app.agents.nodes.scout.models import (
    AGENT,
    MAX_PAGES_JUDGED,
    Node,
    SourceScore,
    one_line,
    page_title,
)
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.web_research import WebResearchState
from app.agents.tools.memory_port import AgentWrite
from app.agents.tools.memory_tools import memory_write
from app.agents.tools.web_port import KEEP_THRESHOLD, SourceVerdictView
from app.core.errors import AppError

PAGE_JUDGE_TIMEOUT_S = 90  # une page trop lente à noter est écartée sans note (D82)
# Le nœud laisse à chaque page son délai complet : au pire toutes les pages notables sont lentes
# (15 × 90 s), plus une minute pour les écritures. Ainsi une page lente est toujours écartée
# seule, jamais avec tout le nœud (D82).
JUDGE_TIMEOUT_S = MAX_PAGES_JUDGED * PAGE_JUDGE_TIMEOUT_S + 60
# Page dont le modèle n'a rendu aucune note conforme au schéma, ou trop lente (revue phase 3, I2).
UNSCORED_REASON = "Note impossible à établir."
INVALID_OUTPUT_CODE = "structured_output_invalid"
PAGE_TIMEOUT_CODE = "page_judge_timeout"

logger = logging.getLogger(__name__)
REMEMBER_TIMEOUT_S = 300  # une vectorisation par source retenue


def _prompt(page: dict[str, Any]) -> str:
    """Titre, métadonnées et texte viennent du web : chacun est encadré (17.4)."""
    sid = page["source_id"]
    meta = "\n".join(
        [
            f"Adresse : {page['url']}",
            f"Auteur : {page['author'] or 'inconnu'}",
            f"Date de publication : {page['date'] or 'inconnue'}",
            f"Langue : {page['lang'] or 'inconnue'}",
        ]
    )
    return render_prompt(
        AGENT,
        mode="judge",
        title=untrusted(page_title(page), f"titre {sid}"),
        meta=untrusted(meta, f"métadonnées {sid}"),
        page=untrusted(page["text"], f"page {sid}"),
        preferred=page["preferred"],
        today=datetime.now(UTC).date().isoformat(),
        threshold=KEEP_THRESHOLD,
    )


def _emit_judged(page: dict[str, Any], verdict: dict[str, Any]) -> None:
    emit(
        "source.found",
        {
            "title": page_title(page),
            "url": page["url"],
            "author": page["author"],
            "date": page["date"],
            "lang": page["lang"],
            "score": verdict["score"],
            "source_id": verdict["source_id"],
            "status": "ok",
            "verdict": verdict["verdict"],
            "reason": verdict["reason"],
        },
        agent=AGENT,
    )


def _page_timeout() -> AppError:
    return AppError(
        PAGE_TIMEOUT_CODE,
        f"La notation d'une page a dépassé {PAGE_JUDGE_TIMEOUT_S:g} secondes.",
        504,
    )


async def _score(model: BaseChatModel, page: dict[str, Any]) -> SourceScore | AppError:
    """Les cinq critères de la page, ou une erreur rendue et non levée : `structured_output_invalid`
    (aucune note conforme au schéma après les essais), ou `page_judge_timeout` (au-delà de
    `PAGE_JUDGE_TIMEOUT_S`). Toute autre erreur (quota, fournisseur indisponible) remonte : elle
    vaudrait pour toutes les pages."""
    limit = asyncio.timeout(PAGE_JUDGE_TIMEOUT_S)
    try:
        async with limit:
            return await structured_call(
                model,
                SourceScore,
                [SystemMessage(_prompt(page)), HumanMessage("Note cette source.")],
                agent=AGENT,
                step="notation",
                intent="je note une source",
            )
    except AppError as exc:
        if exc.code != INVALID_OUTPUT_CODE:
            raise
        return exc
    except TimeoutError:
        if not limit.expired():
            raise  # un délai levé plus bas, pas le nôtre
        return _page_timeout()


async def _record(
    deps: GraphDeps, page: dict[str, Any], score: SourceScore | None
) -> SourceVerdictView:
    """Verdict enregistré par la passerelle ; sans note : écartée, raison fixe (revue phase 3)."""
    return await deps.web.judge(
        deps.user_id,
        deps.session_id,
        page["source_id"],
        criteria=None if score is None else score.criteria,
        reason=UNSCORED_REASON if score is None else score.reason,
        summary="" if score is None else score.summary,
    )


def _entry(
    page: dict[str, Any], score: SourceScore | None, verdict: SourceVerdictView
) -> dict[str, Any]:
    return {
        "source_id": verdict.source_id,
        "url": page["url"],
        "title": page_title(page),
        "lang": page["lang"],
        "summary": one_line(verdict.summary if score is None else score.summary),
        "score": verdict.score,
        "verdict": verdict.verdict,
        "reason": verdict.reason,
    }


def _from_state(page: dict[str, Any]) -> SourceVerdictView | None:
    """Verdict déjà posé dans la session, rendu par la lecture (D82)."""
    known = page.get("verdict")
    if not known:
        return None
    return SourceVerdictView(
        source_id=page["source_id"],
        score=known["score"],
        verdict=known["verdict"],
        reason=known["reason"],
        summary=known.get("summary", ""),
    )


async def _known(deps: GraphDeps, pages: list[dict[str, Any]]) -> dict[str, SourceVerdictView]:
    """Verdicts déjà posés, par `source_id` : ceux que la lecture a rendus (état), puis ceux
    que la base connaît pour les autres pages. Un `judge` coupé au milieu puis rejoué depuis le
    checkpoint de `read` retrouve ainsi les pages déjà notées sans rappeler le modèle (D82)."""
    known = {p["source_id"]: v for p in pages if (v := _from_state(p)) is not None}
    missing = [p["source_id"] for p in pages if p["source_id"] not in known]
    if missing:
        known.update(await deps.web.verdicts(deps.user_id, deps.session_id, missing))
    return known


type PageFailure = tuple[str, str, int, dict[str, Any] | None]
type PageResult = tuple[dict[str, Any], PageFailure | None]


async def _judge_page(
    deps: GraphDeps, model: BaseChatModel, page: dict[str, Any], known: SourceVerdictView | None
) -> PageResult:
    failure = None
    score = None
    if known is None:
        outcome = await _score(model, page)
        if isinstance(outcome, AppError):
            failure = (outcome.code, outcome.message, outcome.status_code, outcome.details)
            logger.warning(
                "Note impossible (%s) : session %s, source %s",
                outcome.code,
                deps.session_id,
                page["source_id"],
            )
        else:
            score = outcome
        known = await _record(deps, page, score)
    return _entry(page, score, known), failure


def make_judge(deps: GraphDeps, *, checkpoint_pages: bool = True) -> Node:
    @node_timeout(JUDGE_TIMEOUT_S)
    async def judge(state: WebResearchState) -> WebResearchState:
        """Une page dont la note est impossible à établir est écartée sans note et la session
        continue ; elle échoue seulement si aucune page n'a pu être notée."""
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        verdicts: list[dict[str, Any]] = []
        failure: PageFailure | None = None
        unscored = 0
        pages = [page for page in state.get("pages", []) if page["source_id"] is not None]
        already = await _known(deps, pages)

        async def judge_source(page: dict[str, Any]) -> PageResult:
            return await _judge_page(deps, model, page, already.get(page["source_id"]))

        # Toujours la même séquence de tâches, même si la base connaît désormais un verdict.
        # Une reprise retrouve le résultat de chaque source terminée avant la source en attente.
        score_page = task(judge_source) if checkpoint_pages else judge_source
        for page in pages:
            entry, error = await score_page(page)
            if "reason" not in entry and (saved := already.get(entry["source_id"])):
                entry = {**entry, "reason": saved.reason}
            _emit_judged(page, entry)
            verdicts.append(entry)
            if error is not None:
                failure, unscored = error, unscored + 1
        if failure is not None and unscored == len(verdicts):
            raise AppError(*failure)
        return {"verdicts": verdicts}

    return judge


def _write_of(verdict: dict[str, Any]) -> AgentWrite:
    """Source retenue, écrite en mémoire (SPEC 4.2 : ne pas la rechercher deux fois). Le même
    contenu rejoué est reconnu : jamais un second élément."""
    lang = verdict["lang"]
    return AgentWrite(
        kind="source",
        title=verdict["title"][:200],
        text=f"{verdict['summary']}\n{verdict['url']}",
        reason=f"Source retenue par l'Éclaireur (score {verdict['score']}/100).",
        tags=(lang,) if lang else (),
        source_id=verdict["source_id"],
    )


def make_remember(deps: GraphDeps) -> Node:
    @node_timeout(REMEMBER_TIMEOUT_S)
    async def remember(state: WebResearchState) -> WebResearchState:
        written = 0
        for verdict in state.get("verdicts", []):
            if verdict["verdict"] == "kept":
                done = await memory_write(deps, _write_of(verdict), agent=AGENT)
                written += done.created
        return {"remembered": written}

    return remember


async def finalize(state: WebResearchState) -> WebResearchState:
    verdicts = state.get("verdicts", [])
    kept = sum(v["verdict"] == "kept" for v in verdicts)
    rejected = len(verdicts) - kept
    unreadable = state.get("unreadable", 0)
    return {
        "summary": f"{kept} source(s) retenue(s), {rejected} écartée(s), {unreadable} illisible(s)."
    }
