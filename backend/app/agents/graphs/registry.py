"""Registre des parcours (graphes d'agents). Un parcours se déclare ici et nulle part ailleurs :
`POST /sessions` valide l'entrée avec `input_model`, le runner compile `build(deps)`."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph import StateGraph
from pydantic import BaseModel

from app.agents.graphs import (
    application_intake,
    application_kit,
    capture,
    conversation,
    cv_capture,
    cv_review,
    daily_brief,
    demo_debate,
    gap_analysis,
    hiring_committee,
    ide_exercise,
    ide_teacher,
    interview,
    learned_document,
    learning_council,
    lesson_factory,
    lesson_hunt,
    market_radar,
    oncall_review,
    podcast,
    program_builder,
    project_brief,
    project_review,
    quiz,
    replan,
    study_session,
    web_research,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.agents.tools.lesson_hunt_port import HUNT_GRAPH
from app.agents.tools.oncall_port import REVIEW_GRAPH
from app.core.errors import AppError


@dataclass(frozen=True)
class GraphSpec:
    name: str
    input_model: type[BaseModel]  # `model_dump()` = état initial
    build: Callable[
        [GraphDeps], StateGraph[Any, Any, Any, Any]
    ]  # non compilé : le runner s'en charge
    # Limite de pas de LangGraph fixée au lancement (`None` : celle de la bibliothèque) : un
    # parcours à boucles la fixe pour qu'une boucle sans fin échoue vite (D159, D160).
    recursion_limit: int | None = None


GRAPHS: dict[str, GraphSpec] = {
    spec.name: spec
    for spec in (
        GraphSpec("demo_debate", demo_debate.DemoDebateInput, demo_debate.build),
        GraphSpec(
            "learned_document", learned_document.LearnedDocumentInput, learned_document.build
        ),
        GraphSpec("web_research", web_research.WebResearchInput, web_research.build),
        GraphSpec(
            "learning_council", learning_council.LearningCouncilInput, learning_council.build
        ),
        GraphSpec("program_builder", program_builder.ProgramBuilderInput, program_builder.build),
        GraphSpec("lesson_factory", lesson_factory.LessonFactoryInput, lesson_factory.build),
        GraphSpec("quiz", quiz.QuizInput, quiz.build),
        GraphSpec("study_session", study_session.StudySessionInput, study_session.build),
        GraphSpec("replan", replan.ReplanInput, replan.build),
        GraphSpec("capture", capture.CaptureInput, capture.build),
        GraphSpec(CONVERSATION_GRAPH, conversation.ConversationInput, conversation.build),
        GraphSpec("gap_analysis", gap_analysis.GapAnalysisInput, gap_analysis.build),
        GraphSpec("cv_capture", cv_capture.CvCaptureInput, cv_capture.build),
        GraphSpec("cv_review", cv_review.CvReviewInput, cv_review.build),
        GraphSpec(
            "application_intake",
            application_intake.ApplicationIntakeInput,
            application_intake.build,
        ),
        GraphSpec("application_kit", application_kit.ApplicationKitInput, application_kit.build),
        GraphSpec("interview", interview.InterviewInput, interview.build),
        GraphSpec(
            "hiring_committee", hiring_committee.HiringCommitteeInput, hiring_committee.build
        ),
        GraphSpec(
            "market_radar",
            market_radar.MarketRadarInput,
            market_radar.build,
            recursion_limit=market_radar.RECURSION_LIMIT,
        ),
        GraphSpec("daily_brief", daily_brief.DailyBriefInput, daily_brief.build),
        GraphSpec(HUNT_GRAPH, lesson_hunt.LessonHuntInput, lesson_hunt.build),
        GraphSpec(REVIEW_GRAPH, oncall_review.OncallReviewInput, oncall_review.build),
        GraphSpec("podcast", podcast.PodcastInput, podcast.build),
        GraphSpec("project_brief", project_brief.ProjectBriefInput, project_brief.build),
        GraphSpec("project_review", project_review.ProjectReviewInput, project_review.build),
        GraphSpec("ide_teacher", ide_teacher.IdeTeacherInput, ide_teacher.build),
        GraphSpec("ide_exercise", ide_exercise.IdeExerciseInput, ide_exercise.build),
    )
}


def get_graph(name: str) -> GraphSpec:
    spec = GRAPHS.get(name)
    if spec is None:
        raise AppError("unknown_graph", f"Parcours inconnu : {name}", 404, {"graph": name})
    return spec
