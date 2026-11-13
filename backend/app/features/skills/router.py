"""API de la carte de compétences (SPEC F15, 14.2 ; D107). Les routes fixes (`graph`, `compare`,
`history`) sont déclarées avant `/skills/{skill_id}`. Tout est filtré par utilisateur : la
compétence ou l'objectif d'un autre donne 404. Lectures sans cache (`Cache-Control: no-store`) :
un changement de niveau se voit à la relecture suivante du front (toutes les 30 s)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUserDep, Db
from app.features.skills.compare import compare_with_goal
from app.features.skills.history import DEFAULT_WEEKS, MAX_WEEKS, skill_history
from app.features.skills.map import skill_detail, skill_graph
from app.features.skills.schemas import (
    CompareOut,
    CompareTarget,
    HistoryOut,
    SkillDetailOut,
    SkillGraphOut,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def clock() -> datetime:
    """Maintenant (UTC) ; remplacé par les tests (`app.dependency_overrides`)."""
    return datetime.now(UTC)


NowDep = Annotated[datetime, Depends(clock)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/graph", response_model=SkillGraphOut)
async def get_graph(current: CurrentUserDep, db: Db, response: Response) -> SkillGraphOut:
    """Compétences (nœuds), prérequis (liens) et radar par domaine. `demand` vaut `null`
    jusqu'au Radar du marché (phase 8)."""
    _no_store(response)
    return await skill_graph(db, current.id)


@router.get("/compare", response_model=CompareOut)
async def get_compare(
    current: CurrentUserDep,
    db: Db,
    response: Response,
    target: CompareTarget = "goal",
    goal_id: Annotated[str | None, Query(max_length=64)] = None,
) -> CompareOut:
    """Moi face au poste cible : les compétences du programme de l'objectif (`goal_id`, sinon
    le plus récent qui a un programme), attendues `valide`. 404 `goal_not_found` ou
    `no_compare_target`."""
    _no_store(response)
    return await compare_with_goal(db, current.id, goal_id)  # `target` : « goal » seul (phase 5)


@router.get("/history", response_model=HistoryOut)
async def get_history(
    current: CurrentUserDep,
    db: Db,
    response: Response,
    now: NowDep,
    weeks: Annotated[int, Query(ge=1, le=MAX_WEEKS)] = DEFAULT_WEEKS,
) -> HistoryOut:
    """Relevés hebdomadaires des `weeks` dernières semaines, plus la semaine en cours en direct."""
    _no_store(response)
    return await skill_history(db, current.id, weeks, now)


@router.get("/{skill_id}", response_model=SkillDetailOut)
async def get_skill(
    skill_id: str, current: CurrentUserDep, db: Db, response: Response, now: NowDep
) -> SkillDetailOut:
    """Détail d'une compétence : preuves, offres (vides jusqu'à la phase 6), prochaine action.
    404 `skill_not_found`."""
    _no_store(response)
    return await skill_detail(db, current.id, skill_id, now)
