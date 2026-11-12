"""Nœuds de l'Éclaireur qui jugent : noter chaque page lue, garder les sources retenues en mémoire,
résumer. La note vient de cinq critères bornés par le schéma ; le code additionne et applique le
seuil de 60 (la passerelle enregistre, SPEC 10.3)."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.scout.models import AGENT, Node, SourceScore, one_line, page_title
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

JUDGE_TIMEOUT_S = 600  # un appel au modèle par page lue
PAGE_JUDGE_TIMEOUT_S = 90  # une page trop lente à noter est écartée sans note (D82)
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


def _emit_judged(page: dict[str, Any], verdict: SourceVerdictView) -> None:
    emit(
        "source.found",
        {
            "title": page_title(page),
            "url": page["url"],
            "author": page["author"],
            "date": page["date"],
            "lang": page["lang"],
            "score": verdict.score,
            "source_id": verdict.source_id,
            "status": "ok",
            "verdict": verdict.verdict,
            "reason": verdict.reason,
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
    }


def _known(page: dict[str, Any]) -> SourceVerdictView | None:
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


def make_judge(deps: GraphDeps) -> Node:
    @node_timeout(JUDGE_TIMEOUT_S)
    async def judge(state: WebResearchState) -> WebResearchState:
        """Une page dont la note est impossible à établir est écartée sans note et la session
        continue ; elle échoue seulement si aucune page n'a pu être notée."""
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        verdicts: list[dict[str, Any]] = []
        failure: AppError | None = None
        unscored = 0
        for page in state.get("pages", []):
            if page["source_id"] is None:
                continue
            if (known := _known(page)) is not None:  # déjà notée : réémise, modèle non rappelé
                _emit_judged(page, known)
                verdicts.append(_entry(page, None, known))
                continue
            outcome = await _score(model, page)
            score = outcome if isinstance(outcome, SourceScore) else None
            if isinstance(outcome, AppError):
                failure, unscored = outcome, unscored + 1
                logger.warning(
                    "Note impossible (%s) : session %s, source %s",
                    outcome.code,
                    deps.session_id,
                    page["source_id"],
                )
            verdict = await _record(deps, page, score)
            _emit_judged(page, verdict)
            verdicts.append(_entry(page, score, verdict))
        if failure is not None and unscored == len(verdicts):
            raise failure  # aucune page notée : la session échoue, message lisible
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
