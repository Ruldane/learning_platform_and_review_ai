"""Propositions du Conseil par lot (SPEC 3.1, étape 5) : écriture idempotente du Stratège (port),
relecture d'un lot rejoué, et lecture du dernier lot pour l'API."""

import builtins
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.council_port import ProposalDraft, ProposalRef, SavedProposal
from app.core.errors import AppError
from app.db.models.learning import Proposal
from app.features.learning.repository import BoardRepository, ProposalRepository
from app.features.learning.schemas import ProposalOut
from app.features.learning.service.goals import owned_goal


def proposal_not_found() -> AppError:
    return AppError("proposal_not_found", "Proposition introuvable.", 404)


def _draft(row: Proposal) -> ProposalDraft:
    return ProposalDraft(
        name=row.name,
        promise=row.promise,
        duration_weeks=row.duration_weeks,
        weekly_hours=row.weekly_hours,
        skills=list(row.skills),
        final_project=row.final_project,
        tradeoffs=list(row.tradeoffs),
    )


def _ref(row: Proposal) -> ProposalRef:
    return ProposalRef(row.id, row.rank, row.name)


async def save_proposals(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    goal_id: str,
    *,
    batch: int,
    proposals: Sequence[ProposalDraft],
) -> list[ProposalRef]:
    """Un lot du Stratège ; idempotent par `(session, lot)` : un lot déjà écrit est rendu tel
    quel, sans ligne de plus."""
    await owned_goal(db, user_id, goal_id)
    repo = ProposalRepository(db, user_id)
    existing = await repo.batch(session_id, batch)
    if existing:
        return [_ref(row) for row in existing]
    refs: list[ProposalRef] = []
    for rank, draft in enumerate(proposals, 1):
        row = await repo.add(
            goal_id=goal_id,
            session_id=session_id,
            batch=batch,
            rank=rank,
            **draft.model_dump(),
        )
        refs.append(_ref(row))
    return refs


async def saved_proposals(
    db: AsyncSession, user_id: str, session_id: str, *, batch: int
) -> list[SavedProposal]:
    rows = await ProposalRepository(db, user_id).batch(session_id, batch)
    return [SavedProposal(_ref(row), _draft(row)) for row in rows]


async def attach_board(db: AsyncSession, user_id: str, proposal_id: str, board_id: str) -> None:
    """La frise du parcours au tableau : proposition, objectif et tableau à l'utilisateur, et
    tableau du même objectif que la proposition (sinon 404)."""
    proposal = await ProposalRepository(db, user_id).get_fresh(proposal_id)
    if proposal is None:
        raise proposal_not_found()
    await owned_goal(db, user_id, proposal.goal_id)
    board = await BoardRepository(db, user_id).get(board_id)
    if board is None or board.goal_id != proposal.goal_id:
        raise AppError("board_not_found", "État du tableau introuvable.", 404)
    proposal.board_id = board_id
    await db.flush()


async def latest_batch(db: AsyncSession, user_id: str, goal_id: str) -> builtins.list[Proposal]:
    """Le dernier lot de l'objectif, par rang ; vide s'il n'y en a pas encore."""
    repo = ProposalRepository(db, user_id)
    latest = await repo.latest_batch(goal_id)
    if latest is None:
        return []
    return await repo.batch(*latest)


async def list_latest(db: AsyncSession, user_id: str, goal_id: str) -> builtins.list[ProposalOut]:
    await owned_goal(db, user_id, goal_id)
    return [ProposalOut.model_validate(row) for row in await latest_batch(db, user_id, goal_id)]


async def proposal_drafts(
    db: AsyncSession, user_id: str, goal_id: str, proposal_ids: Sequence[str]
) -> builtins.list[ProposalDraft]:
    """Les propositions choisies, dans l'ordre, pour le programme (port `ProgramStore`, D88) :
    chacune à l'utilisateur et à l'objectif, sinon 404."""
    repo = ProposalRepository(db, user_id)
    drafts: builtins.list[ProposalDraft] = []
    for proposal_id in proposal_ids:
        row = await repo.get_fresh(proposal_id)
        if row is None or row.goal_id != goal_id:
            raise proposal_not_found()
        drafts.append(_draft(row))
    return drafts
