"""Les réponses du client passent par la publication de leçon et de quiz ordinaires."""

import json

from langchain_core.messages import HumanMessage

from app.core.played import PLAY_CONTEXT, PlayContext
from tests.agents.graphs.council_models import URLS
from tests.agents.graphs.lesson_support import GOOD_LESSON, Lesson, MakeLesson
from tests.agents.graphs.project_support import (
    MakeProject,
    ProjectRun,
    all_met,
    brief_json,
    drafts_json,
    project_models,
)
from tests.agents.graphs.quiz_support import MakeQuiz, QuizRun
from tests.agents.graphs.replan_support import MakeReplan, ReplanRun
from tests.agents.graphs.study_support import MakeStudy, StudyRun
from tests.agents.runtime.runner_helpers import get_session, wait_idle
from tests.support.quiz import ATTEMPT_ID, QUIZ_ID


async def play(run: Lesson | QuizRun | ProjectRun | ReplanRun | StudyRun) -> list[str]:
    factory = run.web.factory if isinstance(run, Lesson) else run.factory
    roles = []
    for _ in range(40):
        await wait_idle(run.runner, run.sid)
        row = await get_session(factory, run.user_id, run.sid)
        assert row.played_by == "claude-code" and row.cost_usd == 0
        if row.status == "completed":
            return roles
        assert row.pending_interrupt, row.error
        if isinstance(run, StudyRun) and row.pending_interrupt["kind"] == "tutor_question":
            await run.answer("Ma réponse.")
            continue
        if isinstance(run, StudyRun) and row.pending_interrupt["kind"] == "finish_session":
            await run.resume("finish")
            continue
        brief = row.pending_interrupt["brief"]
        messages = [HumanMessage(m["content"]) for m in brief["messages"]]
        agent = brief["agent"]
        roles.append(agent)
        schema = (brief["output_schema"] or {}).get("title")
        if schema == "SearchSources":
            answer = json.dumps({"sources": [{"url": u, "title": "Documentation"} for u in URLS]})
        elif schema == "ReadSource":
            answer = json.dumps({"text": "Texte de la page.", "title": "Documentation"})
        else:
            _, answer, _ = run.models.reply(agent, messages)
        await run.runner.submit_step(run.user_id, run.sid, brief["step_id"], answer)
    raise AssertionError("Le parcours ne se termine pas.")


async def test_played_lesson_is_published_after_verification(
    make_lesson_runner: MakeLesson, user_id: str
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        run = await make_lesson_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    assert {"scout", "writer", "verifier"} <= set(await play(run))
    assert len(run.store.published) == 1
    assert run.store.published[0].markdown == GOOD_LESSON.strip()
    assert run.store.published[0].report.problems == ()


async def test_played_examiner_saves_questions_and_cards(
    make_quiz_runner: MakeQuiz, user_id: str
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        run = await make_quiz_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    assert await play(run) == ["examiner"]
    saved = run.store.saved[QUIZ_ID]
    assert len(saved.questions) == 10 and len(saved.flashcards) == 4


async def test_played_quiz_grades_existing_attempt(
    make_quiz_runner: MakeQuiz, user_id: str
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        run = await make_quiz_runner(mode="grade")
    finally:
        PLAY_CONTEXT.reset(flag)
    assert await play(run) == ["examiner"]
    assert ATTEMPT_ID in run.store.graded and run.store.save_grades_calls == 1


async def test_played_project_brief_and_review(project_runner: MakeProject, user_id: str) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        brief = await project_runner(project_models(brief=[brief_json()]), graph="project_brief")
        review = await project_runner(
            project_models(evaluation=[all_met(4)], drafts=[drafts_json()])
        )
    finally:
        PLAY_CONTEXT.reset(flag)
    assert await play(brief) == ["practitioner"]
    assert brief.store.brief_saves == 1
    assert await play(review) == ["practitioner", "practitioner"]
    assert review.store.outcome and review.store.outcome.verdict == "validated"
    assert review.store.review_saves == 1 and review.store.outcome.drafts


async def test_played_replan_reuses_program_rules(
    make_replan_runner: MakeReplan, user_id: str
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        run = await make_replan_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    assert await play(run) == ["strategist"]
    assert run.store.previews and run.store.previews[0].draft.add == []


async def test_played_study_teaches_and_accepts_human_answers(
    make_study_runner: MakeStudy, user_id: str
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        run = await make_study_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    assert set(await play(run)) == {"tutor"}
    assert run.store.finished and run.store.finished.exercise_done
