"""Nœuds de bord du parcours `lesson_factory` (D90) : la fiche du module qui fixe la recherche,
puis la publication, l'échec et le module suivant, tous par le port `LessonStore`.

Chaque écriture du port est idempotente par module : un nœud rejoué après un arrêt (SPEC 9.4)
rend la même chose sans ligne de plus. Aucun effet de bord avant la lecture de la fiche."""

import logging
from dataclasses import asdict, replace

from app.agents.nodes.lesson_common import Node, brief_of, kept_verdicts
from app.agents.nodes.verifier.grades import CRITERIA, MIN_GRADE
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import MAX_SEED_URLS, LessonReport, ResourcePick

MAX_QUERY_CHARS = 300
MAX_REASON_CHARS = 300
MAX_FEEDBACK = 30  # problèmes de contrôle (dont 5 notes) et 20 affirmations au plus
MAX_FEEDBACK_CHARS = 600
PUBLISH_TIMEOUT_S = 300  # le port range la leçon, copie des PDF et rend le PDF de la leçon
NO_SOURCE = "Aucune source fiable (note de 60 ou plus) n'a été trouvée pour ce module."
logger = logging.getLogger(__name__)


def module_query(title: str, skills: tuple[str, ...], theme: str) -> str:
    """La recherche du module : son titre, ses compétences et le thème de la semaine, sur 300
    caractères au plus (coupés à une limite de mot)."""
    text = " ".join(", ".join([title, *skills, theme]).split())
    if len(text) <= MAX_QUERY_CHARS:
        return text
    return text[:MAX_QUERY_CHARS].rsplit(" ", 1)[0].rstrip(",") or text[:MAX_QUERY_CHARS]


def make_brief(deps: GraphDeps) -> Node:
    @node_timeout()
    async def brief(state: LessonFactoryState) -> LessonFactoryState:
        """Fiche du module (port) : la recherche part de son titre, de ses compétences et du
        thème de la semaine, avec les pages du Conseil comme adresses de départ."""
        found = await deps.ports.lessons.brief(deps.user_id, state["module_id"])
        query = module_query(found.title, found.skills, found.week_theme)
        extra: LessonFactoryState = {}
        urls = list(found.seed_urls)
        if state.get("verification"):
            submitted = await deps.ports.lessons.submission(
                deps.user_id, deps.session_id, state["module_id"]
            )
            found = replace(found, title=submitted.title)
            extra = {"draft": submitted.markdown, "citation_urls": list(submitted.urls)}
            urls = list(dict.fromkeys([*submitted.urls, *urls]))
        return {
            **extra,
            "brief": asdict(found),
            "query": query,
            "urls": urls[:MAX_SEED_URLS],
        }

    return brief


def route_resources(state: LessonFactoryState) -> str:
    """Sans aucune source retenue, rien ne peut être écrit ni sourcé : la leçon échoue."""
    if not kept_verdicts(state):
        return "fail_lesson"
    return "verify" if state.get("verification") else "write"


def route_next(state: LessonFactoryState) -> str:
    """Une écriture directe vérifie le module demandé, sans démarrer la chaîne du programme."""
    return "__end__" if state.get("verification") else "next"


def make_publish(deps: GraphDeps) -> Node:
    @node_timeout(PUBLISH_TIMEOUT_S)
    async def publish(state: LessonFactoryState) -> LessonFactoryState:
        """Leçon et ressources rangées par le port (idempotent par module), puis annoncées."""
        brief = brief_of(state)
        report = LessonReport(
            words=state["words"],
            unsupported=(),
            problems=tuple(state.get("resource_notes", [])),
            revisions=state.get("revisions", 0),
            scores=state.get("scores", {}),
        )
        picks = [ResourcePick.model_validate(r) for r in state.get("resources", [])]
        done = await deps.ports.lessons.publish(
            deps.user_id,
            deps.session_id,
            brief.module_id,
            markdown=state["draft"],
            resources=picks,
            report=report,
            verification=state.get("verification", False),
        )
        logger.info(
            "Leçon publiée : session %s, module %s, leçon %s, %d ressource(s)",
            deps.session_id,
            brief.module_id,
            done.lesson_id,
            done.resources,
        )
        pdf = "PDF prêt" if done.pdf_ok else "PDF indisponible pour le moment"
        text = f"Leçon publiée : {state['words']} mots, {done.resources} ressource(s), {pdf}."
        emit("agent.message", {"message_id": "writer-publication", "text": text}, agent="writer")
        emit(
            "artifact.ready",
            {
                "artifact_id": done.lesson_id,
                "kind": "lesson",
                "title": brief.title,
                "url": f"/learn/lessons/{done.lesson_id}",
            },
            agent="writer",
        )
        return {"published": asdict(done), "summary": f"Published the lesson “{brief.title}”."}

    return publish


def _reason(state: LessonFactoryState) -> str:
    if not kept_verdicts(state):
        return NO_SOURCE
    remaining = [*state.get("problems", []), *state.get("unsupported", [])]
    text = f"Contrôles non satisfaits après {state.get('revisions', 0)} révision(s) : "
    if state.get("verification"):
        return (text + ", ".join(_remaining_checks(state)))[:MAX_REASON_CHARS]
    return (text + " ; ".join(remaining))[:MAX_REASON_CHARS]


def _remaining_checks(state: LessonFactoryState) -> list[str]:
    scores = state.get("scores", {})
    items = [
        f"{label} ({scores[key]}/100)"
        for key, label in CRITERIA.items()
        if key in scores and scores[key] < MIN_GRADE
    ]
    items.extend(state.get("check_categories", []))
    if state.get("unsupported"):
        items.append("affirmations non sourcées")
    return items or ["contrôles du chapitre"]


def feedback_of(state: LessonFactoryState) -> list[str]:
    """Remarques du dernier contrôle d'une soumission (D308) : problèmes (dont les notes
    motivées), puis affirmations non sourcées, bornées en nombre et en longueur."""
    remarks = [*state.get("problems", []), *state.get("unsupported", [])]
    return [remark[:MAX_FEEDBACK_CHARS] for remark in remarks[:MAX_FEEDBACK]]


def make_fail_lesson(deps: GraphDeps) -> Node:
    @node_timeout()
    async def fail_lesson(state: LessonFactoryState) -> LessonFactoryState:
        """Leçon en échec, avec sa raison (idempotent) : la chaîne continue quand même."""
        brief = brief_of(state)
        reason = _reason(state)
        verification = state.get("verification", False)
        await deps.ports.lessons.fail(
            deps.user_id,
            deps.session_id,
            brief.module_id,
            reason,
            verification=verification,
            feedback=feedback_of(state) if verification else (),
        )
        logger.info("Leçon en échec : session %s, module %s", deps.session_id, brief.module_id)
        emit(
            "agent.message",
            {"message_id": "writer-echec", "text": f"Leçon non publiée : {reason}"},
            agent="writer",
        )
        summary = (
            "Le brouillon n'a pas été publié."
            if state.get("verification")
            else f"Leçon en échec : « {brief.title} »."
        )
        return {"failure": reason, "summary": summary}

    return fail_lesson


def make_next(deps: GraphDeps) -> Node:
    @node_timeout()
    async def next_lesson(state: LessonFactoryState) -> LessonFactoryState:
        """La chaîne continue, même après un échec : le port lance le module suivant du programme
        (une seule chaîne par programme) et rend son id, ou `None` s'il n'en reste pas."""
        following = await deps.ports.lessons.next_module(
            deps.user_id, state["program_id"], exclude_session_id=deps.session_id
        )
        logger.info(
            "Module suivant : session %s, programme %s, %s",
            deps.session_id,
            state["program_id"],
            following or "aucun",
        )
        return {"next_module": following}

    return next_lesson
