"""Le texte libre des sorties structurées est raccourci, jamais refusé (D97) ; les identifiants,
noms et codes gardent leur plafond strict."""

from typing import Any, get_args

import pytest
from pydantic import BaseModel

from app.agents.nodes.archivist import Concept
from app.agents.nodes.moderator import FramingQuestionModel
from app.agents.nodes.moderator_rounds import RoundPlan, RoundReview
from app.agents.nodes.scout.models import PlannedQuery, SourceScore
from app.agents.nodes.scout.people import PersonModel
from app.agents.nodes.scribe import BoardDraft
from app.agents.nodes.tutor import (
    AnswerCheck,
    FinalQuestion,
    HintTurn,
    SessionSummary,
    TeachTurn,
    TutorReply,
)
from app.agents.runtime.prose import ShortenToMax
from app.agents.tools.council_port import ProposalDraft
from app.agents.tools.lesson_port import ResourcePick
from app.agents.tools.plan_schema import SkillDraft, TaskDraft, WeekDraft
from app.agents.tools.quiz_port import GradeDraft, QuestionDraft, QuizDraft


def _shortens(model: type[BaseModel], name: str) -> bool:
    field = model.model_fields[name]
    found: list[Any] = list(field.metadata)
    for arg in get_args(field.annotation):  # éléments d'une liste : `list[Annotated[...]]`
        found.extend(get_args(arg)[1:])
    return any(isinstance(m, ShortenToMax) for m in found)


@pytest.mark.parametrize(
    ("model", "name"),
    [
        (RoundReview, "summary"),
        (RoundPlan, "intent"),
        (SourceScore, "reason"),
        (SourceScore, "summary"),
        (ProposalDraft, "promise"),
        (ProposalDraft, "final_project"),
        (ProposalDraft, "tradeoffs"),
        (WeekDraft, "objective"),
        (WeekDraft, "deliverable"),
        (TaskDraft, "done_criterion"),
        (ResourcePick, "reason"),
        (FramingQuestionModel, "question"),
        (PersonModel, "role"),
        (Concept, "summary"),
        (QuestionDraft, "expected"),
        (QuestionDraft, "rubric"),
        (QuestionDraft, "explanation"),
        (GradeDraft, "feedback"),
        (TeachTurn, "message"),
        (TeachTurn, "expected"),
        (AnswerCheck, "feedback"),
        (HintTurn, "hint"),
        (FinalQuestion, "expected"),
        (SessionSummary, "summary"),
        (TutorReply, "message"),
    ],
)
def test_free_text_fields_are_shortened(model: type[BaseModel], name: str) -> None:
    assert _shortens(model, name)


@pytest.mark.parametrize(
    ("model", "name"),
    [
        (BoardDraft, "mermaid"),
        (BoardDraft, "title"),
        (PersonModel, "name"),
        (SkillDraft, "name"),
        (PlannedQuery, "text"),
        (ProposalDraft, "name"),
        (ProposalDraft, "skills"),
        (QuestionDraft, "prompt"),
        (QuestionDraft, "choices"),
        (QuestionDraft, "code"),
        (QuestionDraft, "skill"),
        (QuizDraft, "title"),
        (GradeDraft, "ref"),
        (TeachTurn, "question"),
        (TeachTurn, "mermaid"),
        (FinalQuestion, "question"),
    ],
)
def test_identifiers_names_and_code_stay_strict(model: type[BaseModel], name: str) -> None:
    assert not _shortens(model, name)
