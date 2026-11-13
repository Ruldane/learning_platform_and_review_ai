"""Le Tuteur (SPEC F14, 9.1, D102) : sorties structurées, réponses de January aux questions, et ce
que partagent ses nœuds (lecture du contexte, prompts, messages).

Tout texte libre du modèle passe par `Prose` (raccourci, jamais refusé : D97 n° 10), sauf la
question, refusée puis redemandée au-delà de 500 caractères. Le schéma Mermaid n'a pas de plafond
dans le schéma : un refus ferait échouer l'étape ; trop long ou invalide, il est retiré par le code
(`teach`), jamais un échec."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.events import AgentMessagePayload
from app.agents.runtime.prose import Prose
from app.agents.runtime.speech import CitationEntry, extract_citations
from app.agents.runtime.structured import structured_call
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import LessonSection, StudyContext

AGENT = "tutor"
MAX_HINTS = 3
MAX_ANSWER_CHARS = 4000
LESSON_CHARS = 20_000  # une leçon de 2 500 mots tient en entier
TUTOR_QUESTION = "tutor_question"
FINISH_SESSION = "finish_session"
LESSON_LABEL = "leçon"
ANSWER_LABEL = "réponse de January"

TutorAction = Literal["answer", "stuck", "skip", "finish"]


class Node(Protocol):
    async def __call__(self, state: StudySessionState) -> StudySessionState: ...


class TeachTurn(BaseModel):
    message: Prose = Field(min_length=1, max_length=2500)
    question: str = Field(min_length=5, max_length=500)
    expected: Prose = Field(min_length=1, max_length=800)
    mermaid: str | None = None  # sans plafond ici : trop long ou invalide, retiré par le code


class AnswerCheck(BaseModel):
    verdict: Literal["correct", "partial", "wrong"]
    feedback: Prose = Field(min_length=1, max_length=1200)


class HintTurn(BaseModel):
    hint: Prose = Field(min_length=1, max_length=600)


class FinalQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    expected: Prose = Field(min_length=1, max_length=800)


class FinalQuestions(BaseModel):
    """Exactement 3 questions ; au-delà, les 3 premières sont gardées sans échec (m2 de la
    relecture de 5.5) ; moins de 3 reste un refus, redemandé."""

    questions: list[FinalQuestion] = Field(min_length=3, max_length=3)

    @field_validator("questions", mode="before")
    @classmethod
    def _first_three(cls, value: Any) -> Any:
        return value[:3] if isinstance(value, list) else value


class SessionSummary(BaseModel):
    summary: Prose = Field(min_length=1, max_length=700)


class TutorReply(BaseModel):
    """Réponse à une question de January (à l'ouverture, ou par message pendant la séance)."""

    message: Prose = Field(min_length=1, max_length=1500)


@dataclass(frozen=True)
class TutorAnswer:
    action: TutorAction
    text: str = ""


_ACTIONS: dict[Any, TutorAction] = {"stuck": "stuck", "skip": "skip", "finish": "finish"}


def parse_tutor_answer(value: Any) -> TutorAnswer | None:
    """`{"answers": {"answer": texte}}` (texte non vide, coupé à 4 000) → `answer` ; `"stuck"`,
    `"skip"`, `"finish"` (valeur d'une option) ; `{"action": "finish"}` (« Terminer », 5.6) →
    `finish`. Toute autre forme : `None` (la question est reposée)."""
    if isinstance(value, str):
        action = _ACTIONS.get(value)
        return TutorAnswer(action) if action is not None else None
    if not isinstance(value, dict):
        return None
    if value.get("action") == "finish":
        return TutorAnswer("finish")
    answers = value.get("answers")
    text = answers.get("answer") if isinstance(answers, dict) else None
    if isinstance(text, str) and text.strip():
        return TutorAnswer("answer", text.strip()[:MAX_ANSWER_CHARS])
    return None


def context_of(state: StudySessionState) -> StudyContext:
    data = dict(state["context"])
    sections = [LessonSection(**s) for s in data.pop("sections")]
    sources = [CitationEntry(**s) for s in data.pop("sources")]
    return StudyContext(sections=sections, sources=sources, **data)


def section_text(section: LessonSection) -> str:
    return f"## {section.title}\n\n{section.markdown}"


def lesson_prompt(text: str) -> str:
    """Leçon (écrite par le Rédacteur depuis le web) : contenu non fiable, encadré."""
    return untrusted(text[:LESSON_CHARS], LESSON_LABEL)


def whole_lesson(context: StudyContext) -> str:
    parts = [section_text(s) for s in context.sections]
    parts.append(f"## Exercice\n\n{context.exercise}")
    return lesson_prompt("\n\n".join(parts))


def _sources_prompt(sources: list[CitationEntry]) -> str:
    if not sources:
        return "Aucune source citable : ne mets aucun numéro entre crochets."
    return "\n".join(
        f"[{s.index}] " + untrusted(" ".join(s.title.split()), f"source {s.index}") for s in sources
    )


def _module_prompt(context: StudyContext) -> str:
    """Titre et objectifs viennent du programme et de la leçon (sorties d'agents) : encadrés."""
    lines = [f"Titre : {context.module_title}", "Objectifs :"]
    lines += [f"- {objective}" for objective in context.objectives] or ["- aucun précisé"]
    return untrusted("\n".join(lines), "module")


def tutor_prompt(
    state: StudySessionState, task: str, *, memory: bool = False, **variables: object
) -> str:
    """Le prompt du Tuteur pour `task` : module, sources et mode d'étude toujours ; le contexte
    mémoire (déjà encadré par le port) quand `memory`."""
    context = context_of(state)
    return render_prompt(
        AGENT,
        task=task,
        study_mode=context.mode,
        module=_module_prompt(context),
        sources=_sources_prompt(context.sources),
        memory=state.get("memory", "") if memory else "",
        **variables,
    )


async def ask_tutor[T: BaseModel](
    deps: GraphDeps, schema: type[T], prompt: str, request: str, *, step: str, intent: str
) -> T:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        schema,
        [SystemMessage(prompt), HumanMessage(request)],
        agent=AGENT,
        step=step,
        intent=intent,
    )


def say(state: StudySessionState, text: str, message_id: str) -> None:
    """`agent.message` du Tuteur, avec les citations `[n]` des sources de la leçon. Un id fixe
    par étape : rejoué, le message remplace le précédent au lieu de s'ajouter (D57)."""
    sources = context_of(state).sources
    payload = AgentMessagePayload(
        message_id=message_id, text=text, citations=extract_citations(text, sources)
    )
    emit("agent.message", payload, agent=AGENT)


def notes_prompt(notes: list[str]) -> str:
    """Messages de January (non encadrés, D53 §5), une ligne chacun."""
    return "\n".join(f"- {' '.join(note.split())}" for note in notes)


def outcome_record(state: StudySessionState, verdict: str) -> list[dict[str, Any]]:
    """`outcomes` complété du sort de la question en cours."""
    record = {
        "phase": state["phase"],
        "index": state.get("index", 0),
        "question": state["question"],
        "expected": state["expected"],
        "verdict": verdict,
        "hints": state.get("hints", 0),
    }
    return [*state.get("outcomes", []), record]


_VERDICTS = {
    "correct": "juste",
    "partial": "en partie juste",
    "wrong": "fausse",
    "skipped": "passée",
    "revealed": "solution montrée",
}


def outcomes_prompt(state: StudySessionState) -> str:
    """Les questions déjà réglées et leur sort. Les questions viennent du Tuteur, écrites depuis
    une leçon non fiable : encadrées."""
    outcomes = state.get("outcomes", [])
    if not outcomes:
        return "Aucune question réglée pour l'instant."
    lines = [
        f"- {' '.join(o['question'].split())[:300]} : {_VERDICTS[o['verdict']]}, "
        f"{o['hints']} indice(s)"
        for o in outcomes
    ]
    return untrusted("\n".join(lines), "séance")
