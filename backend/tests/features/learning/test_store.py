"""`AgentCouncilStore` (port `CouncilStore` sur la feature `learning`) : écritures idempotentes au
rejeu, filtre utilisateur partout, un seul `program_builder` par objectif."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.council_port import Choice, FramingQuestion, ProposalDraft
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.learning import Board, Goal, Proposal
from app.db.models.program import Program
from app.features.learning.service.runtime import LearningRuntime
from app.features.learning.service.store import AgentCouncilStore

Factory = async_sessionmaker[AsyncSession]
ME, OTHER, SID = "moi", "autre", "council-session"


@dataclass
class FakeLauncher:
    """Crée une vraie ligne de session (`running`), sans lancer de tâche."""

    factory: Factory
    started: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str:
        await asyncio.sleep(0)  # laisse une autre coroutine tenter sa chance
        async with self.factory() as db:
            row = AgentSession(
                user_id=user_id,
                graph=graph,
                status="running",
                input=input,
                subject_type=subject_type,
                subject_id=subject_id,
            )
            db.add(row)
            await db.commit()
        self.started.append((graph, input))
        return row.id


@pytest.fixture
def launcher(db_session_factory: Factory) -> FakeLauncher:
    return FakeLauncher(db_session_factory)


@pytest.fixture
def store(db_session_factory: Factory, launcher: FakeLauncher) -> AgentCouncilStore:
    fake: SessionLauncher = launcher  # type: ignore[assignment]
    return AgentCouncilStore(db_session_factory, fake, LearningRuntime(db_session_factory, fake))


async def _goal(factory: Factory, user_id: str = ME, **fields: Any) -> str:
    async with factory() as db:
        goal = Goal(user_id=user_id, text="Devenir AI product engineer", framing={}, **fields)
        db.add(goal)
        await db.commit()
    return goal.id


async def _count(factory: Factory, model: Any) -> int:
    async with factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


def _draft(name: str) -> ProposalDraft:
    return ProposalDraft(
        name=name,
        promise="Une promesse assez longue.",
        duration_weeks=6,
        weekly_hours=5,
        skills=["Python"],
        final_project="Un projet final démontrable.",
        tradeoffs=["Moins de théorie"],
    )


async def _refused(call: Callable[[], Awaitable[object]], code: str) -> None:
    with pytest.raises(AppError) as caught:
        await call()
    assert caught.value.code == code and caught.value.status_code == 404


async def test_goal_brief_and_framing(
    store: AgentCouncilStore, db_session_factory: Factory
) -> None:
    goal_id = await _goal(
        db_session_factory, target_role="AI PE", deadline=date(2027, 6, 1), weekly_minutes=600
    )
    questions = [FramingQuestion("q1", "Ton niveau en Python ?")]
    await store.save_framing(ME, goal_id, questions, {"q1": "Avancé"})
    await store.save_framing(ME, goal_id, questions, {"q1": "Intermédiaire"})  # écrase
    brief = await store.goal(ME, goal_id)
    assert (brief.text, brief.target_role, brief.weekly_minutes) == (
        "Devenir AI product engineer",
        "AI PE",
        600,
    )
    assert brief.framing == {"q1": "Intermédiaire"}
    await store.save_minutes(ME, goal_id, "Compte rendu")
    await _refused(lambda: store.goal(OTHER, goal_id), "goal_not_found")
    await _refused(lambda: store.save_framing(OTHER, goal_id, [], {}), "goal_not_found")
    await _refused(lambda: store.save_minutes(OTHER, goal_id, "x"), "goal_not_found")


async def test_store_save_board_is_idempotent(
    store: AgentCouncilStore, db_session_factory: Factory
) -> None:
    goal_id = await _goal(db_session_factory)

    async def save(step: int, mermaid: str) -> str:
        return await store.save_board(
            ME, SID, goal_id, step=step, kind="domain_map", title="Carte", mermaid=mermaid
        )

    first = await save(1, "flowchart LR\n  A --> B")
    again = await save(1, "flowchart LR\n  A --> C")  # Scribe rejoué : le dernier écrit gagne
    other_step = await save(2, "flowchart LR\n  X --> Y")
    assert first == again != other_step
    assert await _count(db_session_factory, Board) == 2
    async with db_session_factory() as db:
        board = await db.get(Board, first)
    assert board is not None and board.mermaid.endswith("A --> C") and board.author == "scribe"
    await _refused(
        lambda: store.save_board(
            OTHER, SID, goal_id, step=3, kind="timeline", title="t", mermaid="flowchart LR"
        ),
        "goal_not_found",
    )


async def test_store_save_proposals_is_idempotent_and_replayable(
    store: AgentCouncilStore, db_session_factory: Factory
) -> None:
    goal_id = await _goal(db_session_factory)
    drafts = [_draft("Parcours A"), _draft("Parcours B")]
    refs = await store.save_proposals(ME, SID, goal_id, batch=1, proposals=drafts)
    again = await store.save_proposals(ME, SID, goal_id, batch=1, proposals=[_draft("Autre")])
    assert again == refs and [r.rank for r in refs] == [1, 2]
    assert await _count(db_session_factory, Proposal) == 2
    saved = await store.saved_proposals(ME, SID, batch=1)
    assert [s.ref for s in saved] == refs and [s.draft for s in saved] == drafts
    assert await store.saved_proposals(ME, SID, batch=2) == []
    assert await store.saved_proposals(OTHER, SID, batch=1) == []
    board = await store.save_board(
        ME, SID, goal_id, step=4, kind="timeline", title="Frise", mermaid="flowchart LR"
    )
    await store.attach_board(ME, refs[0].proposal_id, board)
    await _refused(
        lambda: store.attach_board(OTHER, refs[0].proposal_id, board), "proposal_not_found"
    )
    await _refused(
        lambda: store.save_proposals(OTHER, SID, goal_id, batch=3, proposals=drafts),
        "goal_not_found",
    )


async def test_record_choice_marks_exactly_the_choice(
    store: AgentCouncilStore, db_session_factory: Factory
) -> None:
    goal_id = await _goal(db_session_factory)
    drafts = [_draft("Parcours A"), _draft("Parcours B"), _draft("Parcours C")]
    a, b, c = [
        r.proposal_id
        for r in await store.save_proposals(ME, SID, goal_id, batch=1, proposals=drafts)
    ]
    await store.record_choice(ME, SID, goal_id, Choice("mix", (a, c)))
    await store.record_choice(ME, SID, goal_id, Choice("mix", (a, c)))  # rejoué
    async with db_session_factory() as db:
        chosen = set((await db.execute(select(Proposal.id).where(Proposal.chosen))).scalars())
    assert chosen == {a, c}
    await store.record_choice(ME, SID, goal_id, Choice("choose", (b,)))
    async with db_session_factory() as db:
        chosen = set((await db.execute(select(Proposal.id).where(Proposal.chosen))).scalars())
    assert chosen == {b}
    await _refused(
        lambda: store.record_choice(OTHER, SID, goal_id, Choice("choose", (b,))), "goal_not_found"
    )
    await _refused(
        lambda: store.record_choice(ME, "autre-session", goal_id, Choice("choose", (b,))),
        "proposal_not_found",
    )


async def test_start_program_launches_once_with_deduplicated_ids(
    store: AgentCouncilStore, launcher: FakeLauncher, db_session_factory: Factory
) -> None:
    goal_id = await _goal(db_session_factory)
    choice = Choice("mix", ("p1", "p1"), date(2026, 12, 7))
    sids = await asyncio.gather(*(store.start_program(ME, goal_id, choice) for _ in range(3)))
    assert len(set(sids)) == 1
    assert launcher.started == [
        (
            "program_builder",
            {"goal_id": goal_id, "proposal_ids": ["p1"], "start_date": "2026-12-07"},
        )
    ]
    async with db_session_factory() as db:
        goal = await db.get(Goal, goal_id)
    assert goal is not None and goal.status == "chosen"
    await _refused(lambda: store.start_program(OTHER, goal_id, choice), "goal_not_found")


async def test_start_program_returns_existing_session(
    store: AgentCouncilStore, launcher: FakeLauncher, db_session_factory: Factory
) -> None:
    goal_id = await _goal(db_session_factory)
    async with db_session_factory() as db:
        db.add(
            Program(
                user_id=ME,
                goal_id=goal_id,
                title="Programme",
                start_date=date(2026, 12, 7),
                weekly_minutes=600,
                cap_minutes=510,
                session_id="programme-existant",
            )
        )
        await db.commit()
    assert await store.start_program(ME, goal_id, Choice("choose", ("p1",))) == "programme-existant"
    other_goal = await _goal(db_session_factory)
    first = await store.start_program(ME, other_goal, Choice("choose", ("p1",)))
    assert await store.start_program(ME, other_goal, Choice("choose", ("p2",))) == first
    assert len(launcher.started) == 1  # session ouverte rendue telle quelle
