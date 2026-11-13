"""Le Tuteur sans réponse du modèle (contrôle 5.18, D115) : un appel lent, pendu, illisible ou
une panne passagère du fournisseur ne fait jamais échouer la séance.

Chaque appel du Tuteur a son échéance (`TUTOR_CALL_TIMEOUT_S`), plus courte que le plafond du
nœud (120 s) : la marge laisse le repli s'écrire. Un nœud du Tuteur ne fait qu'un appel au
modèle ; au-delà de l'échéance, il n'en refait pas, il se replie (rejoué, il redemande une fois,
comme avant). Les replis viennent de la leçon (section telle qu'écrite, questions tirées des
objectifs et des sections), jamais d'un texte inventé. Une clé refusée, un crédit épuisé ou le
plafond de tokens restent des échecs : la séance ne doit pas continuer sans le dire.
Journaux : identifiants et code d'erreur seulement (SPEC 17.2)."""

import asyncio
import logging

from pydantic import BaseModel

from app.agents.nodes.tutor.models import ask_tutor, context_of
from app.agents.runtime.deps import GraphDeps
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import LessonSection, StudyContext
from app.core.errors import AppError

# Plus court que le plafond d'un nœud (`NODE_TIMEOUT_S`, 120 s) : le repli ne fait que deux
# `emit` (quelques millisecondes), 15 s de marge suffisent aux lectures faites avant l'appel.
TUTOR_CALL_TIMEOUT_S = 105.0
# Lenteur, panne passagère, réponse vide ou illisible : on se replie. Le reste échoue, dont
# `llm_rate_limited` (429 encore là après les nouveaux essais : souvent un quota Z.ai épuisé pour
# la période, que la séance doit dire au lieu de continuer sans correction ; D115 n° 17).
RECOVERABLE_CODES = frozenset(
    {"llm_timeout", "llm_unavailable", "llm_empty_reply", "structured_output_invalid"}
)
UNCHECKED = "Je n'ai pas pu corriger cette réponse, on continue."
NO_REPLY = "Je n'ai pas pu répondre à ton message, on continue."
FALLBACK_FINAL_INTRO = "Trois questions pour finir, tirées des objectifs et des sections."
NO_SOLUTION = "Pas de solution préparée pour cette question : reprends la leçon."
NO_EXPECTED = "(aucune)"  # donnée neutre ; la consigne est dans le prompt (`check`)
MAX_QUESTION_CHARS = 500
MAX_EXPECTED_CHARS = 800

logger = logging.getLogger(__name__)


async def try_tutor[T: BaseModel](
    deps: GraphDeps, schema: type[T], prompt: str, request: str, *, step: str, intent: str
) -> T | None:
    """`ask_tutor` sous l'échéance du Tuteur ; `None` si le modèle n'a pas répondu à temps ou
    lisiblement (le nœud se replie). Les autres erreurs remontent."""
    try:
        async with asyncio.timeout(TUTOR_CALL_TIMEOUT_S):
            return await ask_tutor(deps, schema, prompt, request, step=step, intent=intent)
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Tuteur sans réponse du modèle (%s), repli : session %s, étape %s",
            code,
            deps.session_id,
            step,
        )
        return None


def excerpt(text: str, limit: int = MAX_EXPECTED_CHARS) -> str:
    """`text` coupé à `limit` caractères, sur un espace, avec « … » s'il est coupé."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip() + "…"


def hint_unavailable(level: int, max_hints: int) -> str:
    then = (
        "Redemande « Je bloque » pour l'indice suivant, ou réponds."
        if level < max_hints
        else "Tu peux voir la solution, ou répondre."
    )
    return f"Je n'ai pas pu préparer l'indice {level} sur {max_hints}. {then}"


def section_question(section: LessonSection) -> tuple[str, str]:
    """Question et réponse attendue d'une section, tirées de la leçon."""
    question = f"Que retiens-tu de la section « {section.title} » ? Dis-le avec tes mots."
    return excerpt(question, MAX_QUESTION_CHARS), excerpt(section.markdown) or section.title


def teach_section_as_written(state: StudySessionState) -> tuple[str, str, str]:
    """Message, question et réponse attendue de la section en cours, sans le modèle."""
    section = context_of(state).sections[state["index"]]
    message = (
        "Je n'ai pas pu préparer cette section : la voici telle qu'écrite dans la leçon.\n\n"
        f"## {section.title}\n\n{section.markdown.strip()}"
    )
    question, expected = section_question(section)
    return message, question, expected


def final_questions_from_lesson(context: StudyContext, count: int) -> list[dict[str, str]]:
    """`count` questions finales sans le modèle : les objectifs, puis les sections, puis des
    questions générales sur le module (toujours `count`, jamais de doublon). Seules les questions
    de section ont une réponse attendue (le début de leur section) : les autres n'en ont pas
    (`""`), jugées d'après toute la leçon, sans fiche ni « solution » étrangère (D115 n° 17)."""
    title = context.module_title
    candidates = [(f"Explique avec tes mots : {o.strip()}", "") for o in context.objectives]
    candidates += [section_question(s) for s in context.sections]
    candidates += [
        (f"Qu'as-tu retenu de « {title} » ?", ""),
        (f"Quelle idée de « {title} » vas-tu appliquer, et comment ?", ""),
        (f"Quelle erreur éviter avec « {title} », et pourquoi ?", ""),
    ]
    finals: list[dict[str, str]] = []
    for question, expected in candidates:
        question = excerpt(question, MAX_QUESTION_CHARS)
        if question and all(f["question"] != question for f in finals):
            finals.append({"question": question, "expected": expected})
    return finals[:count]
